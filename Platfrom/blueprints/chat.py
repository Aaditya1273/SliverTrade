"""
SilverTrade AI — AI Chat Blueprint
==================================
AI trading assistant with access to user's real portfolio context.
Uses LLM with function calling to fetch live data as needed.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from flask import Blueprint, jsonify, request, Response, stream_with_context
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from limiter import get_rate_limit
from services.rag_service import rag as rag_service

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__)
limiter = Limiter(key_func=get_remote_address)
API_RATE_LIMIT = get_rate_limit()

# Environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
STRATEGY_HOST = os.getenv("STRATEGY_HOST", "http://strategy:5007")


def get_market_status() -> str:
    """Get current market status (open/closed/pre-market)."""
    # Simple implementation - in production, check actual market hours
    now = datetime.now(timezone.utc)
    hour = now.hour
    if hour >= 9 and hour < 16:
        return "open"
    elif hour >= 8 and hour < 9:
        return "pre-market"
    else:
        return "closed"


def get_funds(apikey: str) -> Optional[Dict[str, Any]]:
    """Get user's funds/balance."""
    try:
        response = requests.post(
            f"{STRATEGY_HOST}/api/v1/funds", json={"apikey": apikey}, timeout=10
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error("Failed to fetch funds: %s", e)
    return None


def get_holdings(apikey: str) -> Optional[List[Dict[str, Any]]]:
    """Get user's holdings."""
    try:
        response = requests.post(
            f"{STRATEGY_HOST}/api/v1/holdings", json={"apikey": apikey}, timeout=10
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error("Failed to fetch holdings: %s", e)
    return None


def get_positions(apikey: str) -> Optional[List[Dict[str, Any]]]:
    """Get user's open positions."""
    try:
        response = requests.post(
            f"{STRATEGY_HOST}/api/v1/positions", json={"apikey": apikey}, timeout=10
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error("Failed to fetch positions: %s", e)
    return None


def get_orderbook(apikey: str, limit: int = 10) -> Optional[List[Dict[str, Any]]]:
    """Get user's recent orders."""
    try:
        response = requests.post(
            f"{STRATEGY_HOST}/api/v1/orderbook", json={"apikey": apikey}, timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            orders = data.get("data", {}).get("orders", data.get("orders", []))
            return orders[:limit]
    except Exception as e:
        logger.error("Failed to fetch orderbook: %s", e)
    return None


def get_recent_signals(limit: int = 5) -> Optional[List[Dict[str, Any]]]:
    """Get recent AI signals from Strategy Engine."""
    try:
        response = requests.get(
            f"{STRATEGY_HOST}/api/v1/signals", params={"limit": limit}, timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("signals", [])
    except Exception as e:
        logger.error("Failed to fetch signals: %s", e)
    return None


def get_tradebook(apikey: str, limit: int = 20) -> Optional[List[Dict[str, Any]]]:
    """Get user's trade history."""
    try:
        response = requests.post(
            f"{STRATEGY_HOST}/api/v1/tradebook", json={"apikey": apikey}, timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            trades = data.get("data", {}).get("trades", data.get("trades", []))
            return trades[:limit]
    except Exception as e:
        logger.error("Failed to fetch tradebook: %s", e)
    return None


def build_user_context(apikey: str, message: str) -> Dict[str, Any]:
    """Collects relevant real-time context for the LLM."""
    context = {}
    message_lower = message.lower()

    # Always included (cheap):
    context["current_time"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    context["market_status"] = get_market_status()

    # Conditionally included based on message keywords:
    if any(kw in message_lower for kw in ["portfolio", "balance", "holding", "position"]):
        context["funds"] = get_funds(apikey)
        context["holdings"] = get_holdings(apikey)
        context["positions"] = get_positions(apikey)

    if any(kw in message_lower for kw in ["order", "trade", "buy", "sell", "placed"]):
        context["recent_orders"] = get_orderbook(apikey, limit=10)

    if any(kw in message_lower for kw in ["signal", "suggest", "recommend", "ai"]):
        context["recent_signals"] = get_recent_signals(limit=5)

    if any(kw in message_lower for kw in ["profit", "loss", "pnl", "performance"]):
        context["tradebook"] = get_tradebook(apikey, limit=20)

    return context


def _retrieve_knowledge(message: str) -> str:
    """Retrieve relevant trading knowledge chunks and format as context block."""
    try:
        chunks = rag_service.retrieve(message, n_results=5)
        if chunks:
            knowledge_block = "\n\nRelevant trading knowledge (use this to inform your answer):\n"
            for i, chunk in enumerate(chunks, 1):
                knowledge_block += f"\n{i}. {chunk}\n"
            return knowledge_block
    except Exception as e:
        logger.warning("Knowledge retrieval failed: %s", e)
    return ""


def _get_openai_client():
    """Create an OpenAI client, using OpenRouter base URL if the key matches.

    Returns:
        Tuple of (openai_client, model_name).
        The model name is adjusted for OpenRouter's vendor-prefixed format.
    """
    import openai

    api_key = OPENAI_API_KEY
    kwargs = {"api_key": api_key}
    # If the key is from OpenRouter, use their base URL
    if api_key.startswith("sk-or-"):
        kwargs["base_url"] = "https://openrouter.ai/api/v1"
        kwargs["default_headers"] = {
            "HTTP-Referer": os.getenv("HOST_SERVER", "http://localhost:5000"),
            "X-Title": "SilverTrade AI",
        }
        model = "openai/gpt-4o-mini"
    else:
        model = "gpt-4o-mini"
    return openai.OpenAI(**kwargs), model


def call_llm(
    message: str, history: List[Dict[str, str]], context: Dict[str, Any]
) -> Dict[str, Any]:
    """Call OpenAI LLM with user context and RAG knowledge."""
    if not OPENAI_API_KEY:
        return {
            "reply": "AI chat is not configured. Please set OPENAI_API_KEY environment variable.",
            "sources": [],
            "suggested_actions": [],
        }

    try:
        client, model = _get_openai_client()

        # Retrieve relevant knowledge chunks
        knowledge = _retrieve_knowledge(message)

        system_prompt = (
            """You are SilverTrade AI, an expert algorithmic trading assistant specializing in Indian equity markets (NSE, BSE, NFO) and cryptocurrency markets.

You have access to the user's real-time portfolio, live market prices, and AI-generated trading signals. You give specific, data-driven advice.

Rules you must ALWAYS follow:
1. NEVER give a generic response. Always reference specific numbers from the user's portfolio or current market data.
2. ALWAYS include relevant risk warnings for leveraged or options trades.
3. NEVER promise specific returns. Say "the signal suggests" or "historically this pattern has shown" — never "you will make X%".
4. If you don't have the data to answer specifically, say what data you need and how the user can find it.
5. Keep responses under 200 words. Be dense with information, not verbose.
6. For order suggestions, always include: entry price, stop loss, target, position size as % of portfolio.
7. Disclaim: "This is not financial advice. Trade responsibly."

User context (real-time data):
"""
            + json.dumps(context, indent=2, default=str)
            + knowledge
        )

        messages = [
            {"role": "system", "content": system_prompt},
        ]

        # Add conversation history
        for msg in history[-5:]:  # Last 5 messages
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current message
        messages.append({"role": "user", "content": message})

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=400,
            temperature=0.4,
        )

        reply = response.choices[0].message.content

        return {"reply": reply, "sources": list(context.keys()), "suggested_actions": []}

    except Exception as e:
        logger.error("LLM call failed: %s", e)
        return {
            "reply": f"AI assistant encountered an error: {str(e)}",
            "sources": [],
            "suggested_actions": [],
        }


@chat_bp.route("/api/v1/chat", methods=["POST"])
@limiter.limit(API_RATE_LIMIT)
def chat():
    """AI trading assistant with access to user's real portfolio context."""
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400

        apikey = data.get("apikey")
        message = data.get("message")
        history = data.get("message_history", [])
        conversation_id = data.get("conversation_id", str(uuid.uuid4()))

        if not apikey or not message:
            return jsonify({"status": "error", "message": "Missing apikey or message"}), 400

        # Build context — what does the AI know about this user right now?
        context = build_user_context(apikey, message)

        # Call LLM with tools
        response = call_llm(message, history, context)

        # Save conversation to database
        try:
            from database.chat_db import save_conversation_message, hash_apikey

            save_conversation_message(
                apikey_hash=hash_apikey(apikey),
                conversation_id=conversation_id,
                user_message=message,
                assistant_reply=response["reply"],
            )
        except Exception as e:
            logger.warning("Failed to save conversation: %s", e)

        return jsonify(
            {
                "status": "success",
                "reply": response["reply"],
                "sources": response["sources"],
                "conversation_id": conversation_id,
                "suggested_actions": response["suggested_actions"],
            }
        )

    except Exception as e:
        logger.exception("Chat error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@chat_bp.route("/api/v1/chat/conversations", methods=["GET"])
@limiter.limit(API_RATE_LIMIT)
def get_conversations():
    """Get user's chat history."""
    try:
        apikey = request.args.get("apikey")
        if not apikey:
            return jsonify({"status": "error", "message": "Missing apikey"}), 400

        from database.chat_db import get_conversations, hash_apikey

        conversations = get_conversations(hash_apikey(apikey), limit=20)

        return jsonify({"status": "success", "data": conversations})

    except Exception as e:
        logger.exception("Get conversations error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@chat_bp.route("/api/v1/chat/conversation", methods=["GET"])
@limiter.limit(API_RATE_LIMIT)
def get_conversation():
    """Get a single conversation by ID."""
    try:
        conversation_id = request.args.get("conversation_id")
        if not conversation_id:
            return jsonify({"status": "error", "message": "Missing conversation_id"}), 400

        from database.chat_db import get_conversation

        conversation = get_conversation(conversation_id)

        if not conversation:
            return jsonify({"status": "error", "message": "Conversation not found"}), 404

        return jsonify({"status": "success", "data": conversation})

    except Exception as e:
        logger.exception("Get conversation error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@chat_bp.route("/api/v1/chat/stream", methods=["GET"])
@limiter.limit(API_RATE_LIMIT)
def chat_stream():
    """Streams LLM response token by token via SSE."""
    try:
        message = request.args.get("message")
        conversation_id = request.args.get("conversation_id", str(uuid.uuid4()))
        apikey = request.args.get("apikey")
        message_history_raw = request.args.get("message_history", "[]")

        if not apikey or not message:
            return jsonify({"status": "error", "message": "Missing apikey or message"}), 400

        # Parse message history from JSON string
        try:
            message_history = json.loads(message_history_raw)
        except (json.JSONDecodeError, TypeError):
            message_history = []

        # Build context
        context = build_user_context(apikey, message)

        def generate():
            full_reply = ""
            conv_id = conversation_id

            if not OPENAI_API_KEY:
                yield f"data: {json.dumps({'token': 'AI chat is not configured. Please set OPENAI_API_KEY.'})}\n\n"
                yield "data: [DONE]\n\n"
                return

            try:
                client, model = _get_openai_client()

                # Retrieve relevant knowledge chunks
                knowledge = _retrieve_knowledge(message)

                system_prompt = (
                    """You are SilverTrade AI, an expert algorithmic trading assistant.
Keep responses under 200 words. Be specific and data-driven.
"""
                    + json.dumps(context, indent=2, default=str)
                    + knowledge
                )

                messages = [
                    {"role": "system", "content": system_prompt},
                ]

                # Add conversation history (last 10 messages)
                for msg in message_history[-10:]:
                    messages.append({"role": msg["role"], "content": msg["content"]})

                messages.append({"role": "user", "content": message})

                stream = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=400,
                    temperature=0.4,
                    stream=True,
                )

                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        full_reply += token
                        yield f"data: {json.dumps({'token': token})}\n\n"

                # Save conversation to database after streaming completes
                try:
                    from database.chat_db import save_conversation_message, hash_apikey

                    save_conversation_message(
                        apikey_hash=hash_apikey(apikey),
                        conversation_id=conv_id,
                        user_message=message,
                        assistant_reply=full_reply,
                    )
                except Exception as db_err:
                    logger.warning("Failed to save streamed conversation: %s", db_err)

                # Send conversation_id as final metadata event
                yield f"data: {json.dumps({'type': 'meta', 'conversation_id': conv_id})}\n\n"
                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error("Streaming error: %s", e)
                yield f"data: {json.dumps({'token': f'Error: {str(e)}'})}\n\n"
                yield "data: [DONE]\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        logger.exception("Chat stream error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500
