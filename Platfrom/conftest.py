"""
Root conftest — shared pytest fixtures for the SilverTrade Platform test suite.

These fixtures provide a test Flask application, test client, and test database
that can be used by any test file in the ``test/`` directory without repeating
boilerplate.

Usage::

    def test_ping(client):
        response = client.get("/api/v1/ping")
        assert response.status_code == 200
"""

import os
import sys
import tempfile

import pytest
from dotenv import load_dotenv

# Ensure the project root is on sys.path so imports like "from database ..."
# work when running pytest from the Platfrom/ directory.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ── Environment ────────────────────────────────────────────────────────────
# Load .env if present (will not override already-set env vars)
load_dotenv(os.path.join(project_root, ".env"))

# Default test environment overrides — these can be overridden by .env or
# by exporting real values before running tests.
_test_env_defaults = {
    "FLASK_DEBUG": "false",
    "LOG_LEVEL": "ERROR",
    "LOG_TO_FILE": "false",
    "APP_KEY": "test_app_key_32_chars_12345678901234",
    "API_KEY_PEPPER": "test_pepper_32_chars_1234567890123456",
    "SECRET_KEY": "test_secret_key_32_chars_1234567890123456",
    "DATABASE_URL": "sqlite://",  # in-memory SQLite for tests
    "REDIS_URL": "",  # Redis optional in tests
    "ORDER_RATE_LIMIT": "1000 per second",  # Disable rate limiting in tests
    "API_RATE_LIMIT": "1000 per second",
    "SMART_ORDER_RATE_LIMIT": "1000 per second",
}

for key, value in _test_env_defaults.items():
    os.environ.setdefault(key, value)


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def app():
    """Create a test Flask application instance.

    Uses the same factory as the production app but with test configuration
    (in-memory SQLite, disabled rate limits, ERROR log level).

    Yields:
        Flask application instance ready for testing.
    """
    # Import the Flask app factory
    from app import create_app

    application = create_app()

    # Push an application context so database.create_all() and url_for()
    # work without a request context.
    ctx = application.app_context()
    ctx.push()

    # Initialize in-memory database tables
    from database.db_config import init_db

    init_db()

    yield application

    # Teardown
    ctx.pop()


@pytest.fixture
def client(app):
    """Create a test HTTP client attached to the Flask application.

    Usage::

        response = client.post("/api/v1/placeorder", json={...})
        assert response.status_code == 400

    Args:
        app: The Flask application from the ``app`` fixture.

    Yields:
        Flask test client.
    """
    with app.test_client() as client:
        yield client


@pytest.fixture
def db_session(app):
    """Provide a clean database session for each test function.

    Opens a transaction that is rolled back after the test completes, so
    tests never leak state to each other.  Uses ``begin()`` (not
    ``begin_nested()``) to avoid requiring a pre-existing transaction.

    Note: the project has multiple ``scoped_session`` instances (user_db,
    traffic_db, leverage_db, etc.).  This fixture only wraps
    ``user_db.db_session``.  Tests that write to other databases need
    their own cleanup.

    Usage::

        def test_insert(db_session):
            from database.user_db import User
            user = User(username="test")
            db_session.add(user)
            db_session.commit()
            assert db_session.query(User).count() == 1

    Args:
        app: The Flask application from the ``app`` fixture.

    Yields:
        SQLAlchemy scoped session bound to the user database.
    """
    from database.user_db import db_session as _db_session

    # Start a transaction explicitly (begin_nested/savepoint is not used
    # because it requires a pre-existing transaction that may not exist).
    _transaction = _db_session.begin()

    yield _db_session

    # Roll back any changes made during the test
    _transaction.rollback()


@pytest.fixture
def api_key(db_session):
    """Create a valid API key for testing authenticated endpoints.

    Uses ``upsert_api_key`` from ``auth_db`` to persist the key in the
    in-memory test database.

    Returns:
        str: A valid API key string.
    """
    import uuid
    from database.auth_db import upsert_api_key

    user_id = "test_user"
    key = str(uuid.uuid4()).replace("-", "")[:32]
    upsert_api_key(user_id, key)
    return key


@pytest.fixture
def auth_payload(api_key):
    """Return a JSON body dict with a valid API key for authenticated POST
    requests.

    Most SilverTrade RESTx API endpoints expect ``apikey`` in the request
    JSON body, not as an HTTP header.  Use this fixture as the base payload
    and add endpoint-specific fields on top::

        payload = {**auth_payload, \"symbol\": \"RELIANCE\", \"exchange\": \"NSE\"}
        response = client.post(\"/api/v1/quotes\", json=payload)

    Args:
        api_key: The API key from the ``api_key`` fixture.

    Returns:
        dict: Base payload dict with ``apikey`` set.
    """
    return {"apikey": api_key}


@pytest.fixture(autouse=True)
def _clean_tempdir():
    """Automatically clean up temporary files created during tests.

    This fixture runs automatically for every test and removes any files
    created in the system temp directory that match the ``test_silvertrade_``
    prefix.  This prevents disk space leaks from export tests.
    """
    import shutil

    yield

    temp_dir = tempfile.gettempdir()
    for name in os.listdir(temp_dir):
        if name.startswith("test_silvertrade_"):
            try:
                path = os.path.join(temp_dir, name)
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
            except OSError:
                pass
