"""
SilverTrade AI — Billing Service Tests
=======================================
Unit tests for the Stripe billing service.

Uses ``unittest.mock`` to simulate Stripe API responses so tests
run without network access or real Stripe credentials.
"""

import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


# ── Helper classes ────────────────────────────────────────────────────────


class MockUser:
    """Simulates a ``database.user_db.User`` instance for billing tests."""
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 1)
        self.username = kwargs.get("username", "test_user")
        self.email = kwargs.get("email", "test@example.com")
        self.plan = kwargs.get("plan", "free")
        self.plan_expires_at = kwargs.get("plan_expires_at", None)
        self.stripe_customer_id = kwargs.get("stripe_customer_id", None)

    def __repr__(self):
        return f"<MockUser id={self.id} email={self.email}>"


# ── Module-level stripe mock ─────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _mock_stripe_module():
    """Inject a mock ``stripe`` module into ``sys.modules`` so that the
    ``import stripe`` inside ``BillingService.__init__`` finds our mock.

    Runs automatically before every test.
    """
    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event = MagicMock(
        return_value=MagicMock(type="customer.subscription.created")
    )
    mock_stripe.Customer.create = MagicMock(
        return_value=MagicMock(id="cus_mock_test_123")
    )
    mock_stripe.Customer.retrieve = MagicMock(
        return_value=MagicMock(
            id="cus_mock_test_123",
            metadata={"user_id": "1"},
        )
    )

    mock_checkout = MagicMock()
    mock_checkout.id = "cs_mock_test_123"
    mock_checkout.url = "https://checkout.stripe.com/pay/cs_mock_test_123"
    mock_stripe.checkout.Session.create = MagicMock(return_value=mock_checkout)

    mock_portal = MagicMock()
    mock_portal.url = "https://billing.stripe.com/session/test_123"
    mock_stripe.billing_portal.Session.create = MagicMock(return_value=mock_portal)

    sys.modules["stripe"] = mock_stripe
    yield
    sys.modules.pop("stripe", None)


# ── Mock database user / db_session context managers ──────────────────────


@contextmanager
def _mock_user_lookup(user_to_return):
    """Context manager that patches ``database.user_db.User``
    and ``database.user_db.db_session`` with mocks.

    ``User.query.get(id)`` returns ``user_to_return``.
    ``db_session`` is a plain MagicMock whose ``.commit()`` is a no-op.

    Yields:
        dict: ``{"db_session": <MagicMock>}`` so callers can assert on commit, etc.
    """
    mock_user_class = MagicMock()
    mock_user_class.query.get.return_value = user_to_return

    mock_db = MagicMock()

    with patch("database.user_db.User", mock_user_class), \
         patch("database.user_db.db_session", mock_db):
        yield {"db_session": mock_db}


def _make_mock_subscription(price_id="price_mock_pro_monthly", user_id="1"):
    """Build a realistic mock Stripe subscription object."""
    sub = MagicMock()
    sub.id = "sub_mock_test_123"
    sub.customer = "cus_mock_test_123"
    sub.metadata = {"user_id": user_id}
    sub.current_period_end = (
        int(datetime.now(timezone.utc).timestamp()) + 2592000
    )

    mock_price = MagicMock()
    mock_price.id = price_id

    mock_item = MagicMock()
    mock_item.price = mock_price

    sub.items.data = [mock_item]

    # Support dict-style access for defensive code paths
    def get_side_effect(key, default=None):
        if key == "items":
            return sub.items
        elif key == "current_period_end":
            return sub.current_period_end
        return default

    sub.get = MagicMock(side_effect=get_side_effect)

    return sub


def _make_mock_event(event_type="customer.subscription.created"):
    """Build a mock Stripe webhook event."""
    ev = MagicMock()
    ev.type = event_type
    ev.data.object = _make_mock_subscription()
    return ev


def _patch_env(monkeypatch, overrides=None):
    """Patch module-level constants in billing_service with test values.

    Must be called before any ``BillingService()`` instantiation.
    """
    import services.billing_service as bs

    defaults = {
        "STRIPE_SECRET_KEY": "sk_test_mock",
        "STRIPE_WEBHOOK_SECRET": "whsec_mock_test",
        "STRIPE_PRO_PRICE_ID": "price_mock_pro_monthly",
        "STRIPE_ENTERPRISE_PRICE_ID": "price_mock_enterprise_monthly",
        "STRIPE_PRO_YEARLY_PRICE_ID": "price_mock_pro_yearly",
        "STRIPE_ENTERPRISE_YEARLY_PRICE_ID": "price_mock_enterprise_yearly",
    }
    if overrides:
        defaults.update(overrides)

    for key, value in defaults.items():
        monkeypatch.setattr(bs, key, value)

    monkeypatch.setattr(bs, "PRICE_ID_TO_PLAN", {
        defaults["STRIPE_PRO_PRICE_ID"]: "pro",
        defaults["STRIPE_ENTERPRISE_PRICE_ID"]: "enterprise",
        defaults["STRIPE_PRO_YEARLY_PRICE_ID"]: "pro",
        defaults["STRIPE_ENTERPRISE_YEARLY_PRICE_ID"]: "enterprise",
    })

    return bs


def _make_service(monkeypatch, env_overrides=None):
    """Helper: patch env & return a fresh BillingService instance."""
    _patch_env(monkeypatch, env_overrides)
    from services.billing_service import BillingService
    return BillingService()


# ═══════════════════════════════════════════════════════════════════════════
# Test Classes
# ═══════════════════════════════════════════════════════════════════════════


class TestInit:
    """BillingService initialization behaviour."""

    def test_init_with_stripe_key(self, monkeypatch):
        service = _make_service(monkeypatch)
        assert service.is_available() is True
        assert service._stripe is not None

    def test_init_without_stripe_key(self, monkeypatch):
        service = _make_service(monkeypatch, {"STRIPE_SECRET_KEY": ""})
        assert service.is_available() is False
        assert service._stripe is None

    def test_init_without_stripe_library(self, monkeypatch):
        """Service should gracefully degrade when stripe cannot be imported."""
        _patch_env(monkeypatch, {"STRIPE_SECRET_KEY": "sk_test_xxx"})

        # Put None in sys.modules so import stripe raises ImportError
        sys.modules["stripe"] = None

        try:
            from services.billing_service import BillingService
            service = BillingService()
            assert service.is_available() is False
            assert service._stripe is None
        finally:
            # Autouse fixture will reset sys.modules["stripe"]
            pass


class TestIsAvailable:
    def test_available(self, monkeypatch):
        service = _make_service(monkeypatch)
        assert service.is_available() is True

    def test_unavailable(self, monkeypatch):
        service = _make_service(monkeypatch, {"STRIPE_SECRET_KEY": ""})
        assert service.is_available() is False


class TestCreateCustomer:
    def test_create_customer_success(self, monkeypatch):
        """Should create Stripe customer and update user record."""
        service = _make_service(monkeypatch)
        user = MockUser(id=42, email="bill_test_c1@example.com")

        with _mock_user_lookup(user) as mocks:
            customer_id = service.create_customer(user.id, user.email)

        assert customer_id == "cus_mock_test_123"
        assert user.stripe_customer_id == "cus_mock_test_123"
        mocks["db_session"].commit.assert_called_once()

    def test_create_customer_service_unavailable(self, monkeypatch):
        """Should return None when service is unavailable."""
        service = _make_service(monkeypatch, {"STRIPE_SECRET_KEY": ""})
        assert service.create_customer(1, "test@example.com") is None

    def test_create_customer_user_not_found(self, monkeypatch):
        """Should return customer ID even if user not found in local DB."""
        service = _make_service(monkeypatch)

        with _mock_user_lookup(None):
            customer_id = service.create_customer(99999, "nonexistent@example.com")

        assert customer_id == "cus_mock_test_123"

    def test_create_customer_stripe_error(self, monkeypatch):
        """Should return None when Stripe API call fails."""
        sys.modules["stripe"].Customer.create.side_effect = Exception("Stripe API error")
        service = _make_service(monkeypatch)
        user = MockUser(id=42, email="bill_test_c2@example.com")

        with _mock_user_lookup(user):
            result = service.create_customer(user.id, user.email)

        assert result is None


class TestCreateCheckoutSession:
    """Tests for all 4 plan/interval combos and edge cases."""

    def _checkout(self, monkeypatch, plan, interval,
                  user_kwargs=None, expected_url=True):
        """Helper: create a checkout session for a plan/interval and assert url."""
        service = _make_service(monkeypatch)
        kwargs = {"id": 1, "email": "c@test.com", "stripe_customer_id": "cus_existing_123"}
        if user_kwargs:
            kwargs.update(user_kwargs)
        user = MockUser(**kwargs)

        with _mock_user_lookup(user):
            url = service.create_checkout_session(user.id, plan, interval)

        if expected_url:
            assert url == "https://checkout.stripe.com/pay/cs_mock_test_123"
        else:
            assert url is None
        return url

    def test_pro_monthly(self, monkeypatch):
        self._checkout(monkeypatch, "pro", "month")

    def test_pro_yearly(self, monkeypatch):
        self._checkout(monkeypatch, "pro", "year")

    def test_enterprise_monthly(self, monkeypatch):
        self._checkout(monkeypatch, "enterprise", "month")

    def test_enterprise_yearly(self, monkeypatch):
        self._checkout(monkeypatch, "enterprise", "year")

    def test_user_not_found(self, monkeypatch):
        service = _make_service(monkeypatch)
        with _mock_user_lookup(None):
            result = service.create_checkout_session(99999, "pro", "month")
        assert result is None

    def test_unknown_plan(self, monkeypatch):
        self._checkout(monkeypatch, "ultimate_mega_plan", "month",
                       expected_url=False)

    def test_service_unavailable(self, monkeypatch):
        service = _make_service(monkeypatch, {"STRIPE_SECRET_KEY": ""})
        assert service.create_checkout_session(1, "pro", "month") is None

    def test_existing_stripe_customer_reused(self, monkeypatch):
        """Should reuse existing stripe_customer_id without creating a new customer."""
        self._checkout(monkeypatch, "pro", "month",
                       user_kwargs={"stripe_customer_id": "cus_existing_123"})
        assert sys.modules["stripe"].Customer.create.call_count == 0

    def test_auto_create_customer_when_missing(self, monkeypatch):
        """Should auto-create Stripe customer when user has no stripe_customer_id."""
        service = _make_service(monkeypatch)
        user = MockUser(id=1, email="c8@test.com")  # No stripe_customer_id

        with _mock_user_lookup(user):
            url = service.create_checkout_session(user.id, "pro", "month")

        assert url == "https://checkout.stripe.com/pay/cs_mock_test_123"
        assert user.stripe_customer_id == "cus_mock_test_123"


class TestHandleWebhook:
    def test_valid_webhook(self, monkeypatch):
        """Should return True for a valid webhook event."""
        service = _make_service(monkeypatch)
        result = service.handle_webhook(b"{}", "test_sig")
        assert result is True
        sys.modules["stripe"].Webhook.construct_event.assert_called_once_with(
            b"{}", "test_sig", "whsec_mock_test"
        )

    def test_webhook_missing_secret(self, monkeypatch):
        """Should return False when STRIPE_WEBHOOK_SECRET is not configured."""
        service = _make_service(monkeypatch, {"STRIPE_WEBHOOK_SECRET": ""})
        result = service.handle_webhook(b"{}", "test_sig")
        assert result is False
        assert sys.modules["stripe"].Webhook.construct_event.call_count == 0

    def test_webhook_invalid_signature(self, monkeypatch):
        """Should return False when signature validation fails."""
        sys.modules["stripe"].Webhook.construct_event.side_effect = Exception("Bad sig")
        service = _make_service(monkeypatch)
        result = service.handle_webhook(b"{}", "bad_sig")
        assert result is False

    def test_webhook_service_unavailable(self, monkeypatch):
        """Should return False when Stripe is not available."""
        service = _make_service(monkeypatch, {"STRIPE_SECRET_KEY": ""})
        assert service.handle_webhook(b"{}", "test_sig") is False

    def test_webhook_unhandled_event(self, monkeypatch):
        """Should return True even for unhandled event types (no crash)."""
        sys.modules["stripe"].Webhook.construct_event.return_value = \
            _make_mock_event("charge.refunded")
        service = _make_service(monkeypatch)
        result = service.handle_webhook(b"{}", "test_sig")
        assert result is True


class TestActivateSubscription:
    def _activate(self, monkeypatch, user_kwargs, price_id, user_id):
        """Helper: set up & run _activate_subscription."""
        service = _make_service(monkeypatch)
        user = MockUser(**user_kwargs)

        with _mock_user_lookup(user):
            sub = _make_mock_subscription(price_id=price_id, user_id=user_id)
            service._activate_subscription(sub)

        return user

    def test_activate_pro_subscription(self, monkeypatch):
        """Should activate user with 'pro' plan."""
        user = self._activate(
            monkeypatch,
            {"id": 10, "email": "act_1@test.com", "stripe_customer_id": "cus_mock"},
            "price_mock_pro_monthly", "10",
        )
        assert user.plan == "pro"
        assert user.plan_expires_at is not None

    def test_activate_enterprise_subscription(self, monkeypatch):
        """Should activate user with 'enterprise' plan."""
        user = self._activate(
            monkeypatch,
            {"id": 11, "email": "act_2@test.com", "stripe_customer_id": "cus_mock"},
            "price_mock_enterprise_monthly", "11",
        )
        assert user.plan == "enterprise"

    def test_activate_fallback_to_customer_metadata(self, monkeypatch):
        """Should fall back to Customer.retrieve for user_id."""
        sys.modules["stripe"].Customer.retrieve.return_value = MagicMock(
            id="cus_mock_test_123",
            metadata={"user_id": "42"},
        )

        user = self._activate(
            monkeypatch,
            {"id": 42, "email": "act_3@test.com", "stripe_customer_id": "cus_mock"},
            "price_mock_pro_monthly", "",  # No user_id in subscription
        )
        sys.modules["stripe"].Customer.retrieve.assert_called_once_with("cus_mock_test_123")
        assert user.plan == "pro"

    def test_activate_no_user_found(self, monkeypatch):
        """Should not crash when subscription references non-existent user."""
        service = _make_service(monkeypatch)

        with _mock_user_lookup(None):
            sub = _make_mock_subscription(user_id="99999")
            service._activate_subscription(sub)  # Should not raise

    def test_activate_unknown_price_id_defaults_to_pro(self, monkeypatch):
        """Should default to 'pro' when price ID is unknown."""
        user = self._activate(
            monkeypatch,
            {"id": 13, "email": "act_4@test.com", "stripe_customer_id": "cus_mock"},
            "price_unknown_xyz", "13",
        )
        assert user.plan == "pro"  # Default


class TestDeactivateSubscription:
    def test_deactivate_subscription(self, monkeypatch):
        """Should set user plan to 'free' on cancellation."""
        service = _make_service(monkeypatch)
        user = MockUser(
            id=20,
            email="deact_1@test.com",
            stripe_customer_id="cus_mock_test_123",
            plan="pro",
            plan_expires_at=datetime.now(timezone.utc),
        )

        with _mock_user_lookup(user) as mocks:
            sub = _make_mock_subscription(user_id="20")
            service._deactivate_subscription(sub)

        assert user.plan == "free"
        assert user.plan_expires_at is None
        mocks["db_session"].commit.assert_called_once()

    def test_deactivate_no_user_id(self, monkeypatch):
        """Should not crash when subscription has no user_id metadata."""
        service = _make_service(monkeypatch)
        with _mock_user_lookup(None):
            sub = _make_mock_subscription(user_id="")
            service._deactivate_subscription(sub)  # Should not raise

    def test_deactivate_fallback_to_customer_metadata(self, monkeypatch):
        """Should fall back to Customer.retrieve for user_id on deactivation."""
        sys.modules["stripe"].Customer.retrieve.return_value = MagicMock(
            id="cus_mock_test_123",
            metadata={"user_id": "42"},
        )
        service = _make_service(monkeypatch)
        user = MockUser(
            id=42,
            email="deact_2@test.com",
            stripe_customer_id="cus_mock_test_123",
            plan="pro",
            plan_expires_at=datetime.now(timezone.utc),
        )

        with _mock_user_lookup(user):
            sub = _make_mock_subscription(user_id="")
            service._deactivate_subscription(sub)

        sys.modules["stripe"].Customer.retrieve.assert_called_once_with("cus_mock_test_123")
        assert user.plan == "free"


class TestSubscriptionLifecycleStubs:
    """These methods are currently stubs (TODO). Verify they don't crash."""

    def test_update_subscription(self, monkeypatch):
        service = _make_service(monkeypatch)
        service._update_subscription(_make_mock_subscription())

    def test_handle_payment_failure(self, monkeypatch):
        service = _make_service(monkeypatch)
        service._handle_payment_failure(MagicMock(id="in_mock_123"))

    def test_handle_payment_success(self, monkeypatch):
        service = _make_service(monkeypatch)
        service._handle_payment_success(MagicMock(id="in_mock_123"))


class TestCreateCustomerPortalSession:
    def test_portal_success(self, monkeypatch):
        """Should create a Customer Portal session URL."""
        service = _make_service(monkeypatch)
        user = MockUser(id=1, email="portal_1@test.com",
                        stripe_customer_id="cus_mock_test_123")

        with _mock_user_lookup(user):
            url = service.create_customer_portal_session(user.id)

        assert url == "https://billing.stripe.com/session/test_123"

    def test_portal_no_stripe_customer(self, monkeypatch):
        """Should return None when user has no stripe_customer_id."""
        service = _make_service(monkeypatch)
        user = MockUser(id=1, email="portal_2@test.com")  # No stripe_customer_id

        with _mock_user_lookup(user):
            result = service.create_customer_portal_session(user.id)

        assert result is None

    def test_portal_user_not_found(self, monkeypatch):
        """Should return None when user does not exist."""
        service = _make_service(monkeypatch)

        with _mock_user_lookup(None):
            result = service.create_customer_portal_session(99999)

        assert result is None

    def test_portal_service_unavailable(self, monkeypatch):
        """Should return None when Stripe is not available."""
        service = _make_service(monkeypatch, {"STRIPE_SECRET_KEY": ""})
        assert service.create_customer_portal_session(1) is None
