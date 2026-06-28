import asyncio
import atexit
import os
import platform
import signal
import sys
import threading

from utils.logging import get_logger, highlight_url

from .server import main as websocket_main

# Import the original threading module to run the asyncio event loop in a real
# OS thread, bypassing eventlet's monkey-patching which turns threading.Thread
# into green threads where asyncio.new_event_loop() cannot work.
if "eventlet" in sys.modules:
    import eventlet

    _original_threading = eventlet.patcher.original("threading")
else:
    _original_threading = threading

# Set the correct event loop policy for Windows to avoid ZeroMQ warnings
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Global flag to track if the WebSocket server has been started
# Used to prevent multiple instances in Flask debug mode
_websocket_server_started = False
_websocket_proxy_instance = None
_websocket_thread = None

logger = get_logger(__name__)


# Check if we're in the Flask child process that should start the WebSocket server
def should_start_websocket():
    """
    Determine if the current process should start the WebSocket server

    In Flask debug mode with reloader enabled, we only want to start the
    WebSocket server in the child process, not the parent process that
    monitors for file changes.

    Returns:
        bool: True if we should start the WebSocket server, False otherwise
    """
    # In debug mode, only start in the Flask child process
    if os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true"):
        # WERKZEUG_RUN_MAIN is set to 'true' by Flask in the child process
        # that actually runs the application
        return os.environ.get("WERKZEUG_RUN_MAIN") == "true"

    # In non-debug mode, always start
    return True


def cleanup_websocket_server():
    """Clean up WebSocket server resources with coordinated shutdown sequence.

    Shutdown sequence:
    1. Stop accepting new connections (set running flag)
    2. Disconnect all broker adapters (graceful, 3s timeout per adapter)
    3. Close all client WebSocket connections (2s timeout)
    4. Close WebSocket server to release the port (2s timeout)
    5. Close ZMQ socket and context (1s timeout each)
    6. Clean up shared ZMQ context
    7. Join the WebSocket thread (5s timeout)

    Each step is isolated so a failure in one doesn't block the others.
    """
    global _websocket_proxy_instance, _websocket_thread

    if _websocket_proxy_instance is None and (
        _websocket_thread is None or not _websocket_thread.is_alive()
    ):
        logger.debug("WebSocket server already cleaned up — skipping")
        return

    logger.info("=== Beginning graceful WebSocket shutdown ===")

    # ── Step 0: Stop accepting new connections ──────────────────────────
    if _websocket_proxy_instance:
        _websocket_proxy_instance.running = False
        logger.info("Step 0: Set running=False — stopped accepting new connections")

    # ── Step 1: Disconnect all broker adapters ──────────────────────────
    if _websocket_proxy_instance and hasattr(_websocket_proxy_instance, "broker_adapters"):
        adapter_count = len(_websocket_proxy_instance.broker_adapters)
        if adapter_count > 0:
            logger.info(f"Step 1: Disconnecting {adapter_count} broker adapter(s)")
            for user_id in list(_websocket_proxy_instance.broker_adapters.keys()):
                try:
                    adapter = _websocket_proxy_instance.broker_adapters.pop(user_id, None)
                    if adapter and hasattr(adapter, "disconnect"):
                        import threading as _t

                        t = _t.Thread(target=lambda a=adapter: a.disconnect(), daemon=True)
                        t.start()
                        t.join(timeout=3.0)
                        if t.is_alive():
                            logger.warning(f"    Adapter disconnect for user {user_id} timed out")
                        else:
                            logger.info(f"    Disconnected adapter for user {user_id}")
                except Exception as e:
                    logger.warning(f"    Error disconnecting adapter for user {user_id}: {e}")
        else:
            logger.info("Step 1: No broker adapters to disconnect")

    # ── Step 2: Close WebSocket server (release port) ───────────────────
    if _websocket_proxy_instance and hasattr(_websocket_proxy_instance, "server"):
        try:
            server = _websocket_proxy_instance.server
            if server is not None:
                logger.info("Step 2: Closing WebSocket server (releasing port)")
                server.close()
                # Attempt async wait with timeout via a short-lived event loop
                try:
                    try:
                        asyncio.get_running_loop()
                        logger.debug("    Running inside an event loop — scheduling wait_closed()")
                    except RuntimeError:
                        _temp_loop = asyncio.new_event_loop()
                        try:
                            _temp_loop.run_until_complete(
                                asyncio.wait_for(server.wait_closed(), timeout=2.0)
                            )
                            logger.info("    WebSocket server closed (port released)")
                        except asyncio.TimeoutError:
                            logger.warning("    Timeout waiting for server to close")
                        finally:
                            _temp_loop.close()
                except Exception as e:
                    logger.warning(f"    Error during server close wait: {e}")
        except Exception as e:
            logger.warning(f"    Error closing server: {e}")

    # ── Step 3: Close all client connections ────────────────────────────
    if _websocket_proxy_instance and hasattr(_websocket_proxy_instance, "clients"):
        client_count = len(_websocket_proxy_instance.clients)
        if client_count > 0:
            logger.info(f"Step 3: Closing {client_count} client connection(s)")
            for client_id, ws in list(_websocket_proxy_instance.clients.items()):
                try:
                    if hasattr(ws, "open") and ws.open:
                        try:
                            asyncio.get_running_loop()
                            # Schedule close on existing loop
                            asyncio.run_coroutine_threadsafe(ws.close(), asyncio.get_running_loop())
                        except RuntimeError:
                            pass  # No loop — connection will be cleaned up by OS
                except Exception:
                    pass
            _websocket_proxy_instance.clients.clear()
            logger.info("    Client connections closed")
        else:
            logger.info("Step 3: No clients to disconnect")

    # ── Step 4: Close ZMQ socket and context ────────────────────────────
    if _websocket_proxy_instance:
        try:
            if hasattr(_websocket_proxy_instance, "socket"):
                import zmq

                sock = _websocket_proxy_instance.socket
                if sock is not None:
                    logger.info("Step 4a: Closing ZMQ socket")
                    try:
                        sock.setsockopt(zmq.LINGER, 0)
                        sock.close()
                    except Exception as e:
                        logger.warning(f"    Error closing ZMQ socket: {e}")

            if hasattr(_websocket_proxy_instance, "context"):
                ctx = _websocket_proxy_instance.context
                if ctx is not None:
                    logger.info("Step 4b: Terminating ZMQ context")
                    try:
                        ctx.term()
                    except Exception as e:
                        logger.warning(f"    Error terminating ZMQ context: {e}")
        except Exception as e:
            logger.warning(f"    Error during ZMQ cleanup: {e}")

        _websocket_proxy_instance = None

    # ── Step 5: Clean up shared ZMQ context ─────────────────────────────
    try:
        from .base_adapter import BaseBrokerWebSocketAdapter

        logger.info("Step 5: Cleaning up shared ZMQ context")
        BaseBrokerWebSocketAdapter.cleanup_shared_context()
    except Exception as e:
        logger.warning(f"    Error cleaning up shared ZMQ context: {e}")

    # ── Step 6: Close all WebSocket client singletons ───────────────────
    try:
        from services.websocket_client import close_all_clients

        logger.info("Step 6: Closing all WebSocket client connections")
        close_all_clients()
    except Exception as e:
        logger.warning(f"    Error closing WebSocket clients: {e}")

    # ── Step 7: Join the WebSocket thread ───────────────────────────────
    if _websocket_thread and _websocket_thread.is_alive():
        logger.info("Step 7: Waiting for WebSocket thread to finish...")
        _websocket_thread.join(timeout=5.0)
        if _websocket_thread.is_alive():
            logger.warning("    WebSocket thread did not finish within 5s — detaching")
        else:
            logger.info("    WebSocket thread joined successfully")
        _websocket_thread = None

    logger.info("=== WebSocket graceful shutdown complete ===")


def signal_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) and SIGTERM signals"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    cleanup_websocket_server()
    # Use os._exit() for immediate termination across all platforms
    os._exit(0)


def start_websocket_server():
    """
    Start the WebSocket proxy server in a separate thread.
    This function should be called when the Flask app starts.
    """
    global _websocket_proxy_instance, _websocket_thread

    logger.debug("Starting WebSocket proxy server in a separate thread")

    def run_websocket_server():
        """Run the WebSocket server in an event loop"""
        global _websocket_proxy_instance
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Import here to avoid circular imports
            import os

            from dotenv import load_dotenv

            from .server import WebSocketProxy

            load_dotenv()
            ws_host = os.getenv("WEBSOCKET_HOST", "127.0.0.1")
            ws_port = int(os.getenv("WEBSOCKET_PORT", "8765"))

            # Create and store the proxy instance
            _websocket_proxy_instance = WebSocketProxy(host=ws_host, port=ws_port)

            # Start the proxy
            loop.run_until_complete(_websocket_proxy_instance.start())

        except Exception as e:
            logger.exception(f"Error in WebSocket server thread: {e}")
            _websocket_proxy_instance = None
        finally:
            # Always close the event loop to prevent FD leak
            if loop is not None:
                try:
                    # Cancel all pending tasks
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    # Run until all tasks are cancelled
                    if pending:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    loop.close()
                    logger.debug("Event loop closed successfully")
                except Exception as loop_err:
                    logger.warning(f"Error closing event loop: {loop_err}")

    # Start the WebSocket server in a daemon thread
    _websocket_thread = _original_threading.Thread(
        target=run_websocket_server,
        daemon=False,  # Changed to False so we can properly clean up
    )
    _websocket_thread.start()

    # Register cleanup handlers
    atexit.register(cleanup_websocket_server)

    # Register signal handlers for graceful shutdown
    try:
        # SIGINT (Ctrl+C) - Available on all platforms
        signal.signal(signal.SIGINT, signal_handler)
        signals_registered = ["SIGINT"]

        # SIGTERM - Available on Unix-like systems (Mac, Linux)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, signal_handler)
            signals_registered.append("SIGTERM")

        logger.debug(f"Signal handlers registered: {', '.join(signals_registered)}")
    except Exception as e:
        logger.warning(f"Could not register signal handlers: {e}")

    logger.debug("WebSocket proxy server thread started")
    return _websocket_thread


def start_websocket_proxy(app):
    """
    Integrate the WebSocket proxy server with a Flask application.
    This should be called during app initialization.

    Args:
        app: Flask application instance
    """
    global _websocket_server_started

    # Check if this process should start the WebSocket server
    if should_start_websocket():
        # Our flag will prevent multiple starts if called multiple times
        if not _websocket_server_started:
            _websocket_server_started = True
            logger.debug("Starting WebSocket server in Flask application process")
            start_websocket_server()
            logger.debug("WebSocket server integration with Flask complete")
        else:
            logger.debug("WebSocket server already running, skipping initialization")
    else:
        logger.debug("Skipping WebSocket server in parent/monitor process")
