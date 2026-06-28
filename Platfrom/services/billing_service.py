"""
SilverTrade AI — Billing Service
================================
Stripe billing integration for subscription management.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Stripe API key from environment
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Price IDs for plans (to be configured in Stripe dashboard)
STRIPE_PRO_PRICE_ID = os.getenv("STRIPE_PRO_PRICE_ID")
STRIPE_ENTERPRISE_PRICE_ID = os.getenv("STRIPE_ENTERPRISE_PRICE_ID")
STRIPE_PRO_YEARLY_PRICE_ID = os.getenv("STRIPE_PRO_YEARLY_PRICE_ID")
STRIPE_ENTERPRISE_YEARLY_PRICE_ID = os.getenv("STRIPE_ENTERPRISE_YEARLY_PRICE_ID")

# Map price IDs to plan names for detection in webhooks
PRICE_ID_TO_PLAN = {
    STRIPE_PRO_PRICE_ID: "pro",
    STRIPE_ENTERPRISE_PRICE_ID: "enterprise",
    STRIPE_PRO_YEARLY_PRICE_ID: "pro",
    STRIPE_ENTERPRISE_YEARLY_PRICE_ID: "enterprise",
}


class BillingService:
    """Stripe billing service for subscription management."""

    def __init__(self):
        self._stripe = None
        if STRIPE_SECRET_KEY:
            try:
                import stripe

                stripe.api_key = STRIPE_SECRET_KEY
                self._stripe = stripe
                logger.info("Stripe billing service initialized")
            except ImportError:
                logger.warning("Stripe library not installed. Billing features disabled.")
        else:
            logger.warning("STRIPE_SECRET_KEY not set. Billing features disabled.")

    def is_available(self) -> bool:
        """Check if Stripe is configured and available."""
        return self._stripe is not None

    def create_customer(self, user_id: int, email: str) -> Optional[str]:
        """Create Stripe customer, store ID in user record.

        Returns customer ID or None if failed.
        """
        if not self.is_available():
            logger.warning("Stripe not available for customer creation")
            return None

        try:
            customer = self._stripe.Customer.create(email=email, metadata={"user_id": str(user_id)})

            # Update user record with Stripe customer ID
            from database.user_db import User, db_session

            user = User.query.get(user_id)
            if user:
                user.stripe_customer_id = customer.id
                db_session.commit()

            logger.info(f"Created Stripe customer {customer.id} for user {user_id}")
            return customer.id
        except Exception as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            return None

    def create_checkout_session(
        self, user_id: int, plan: str, interval: str = "month"
    ) -> Optional[str]:
        """Returns Stripe Checkout URL for the selected plan.

        Args:
            user_id: User's database ID.
            plan: "pro" or "enterprise".
            interval: "month" or "year".

        Returns checkout URL or None if failed.
        """
        if not self.is_available():
            logger.warning("Stripe not available for checkout")
            return None

        try:
            from database.user_db import User

            user = User.query.get(user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return None

            # Get or create Stripe customer
            customer_id = user.stripe_customer_id
            if not customer_id:
                customer_id = self.create_customer(user_id, user.email)
                if not customer_id:
                    return None

            # Get price ID for plan + interval
            price_ids = {
                ("pro", "month"): STRIPE_PRO_PRICE_ID,
                ("pro", "year"): STRIPE_PRO_YEARLY_PRICE_ID,
                ("enterprise", "month"): STRIPE_ENTERPRISE_PRICE_ID,
                ("enterprise", "year"): STRIPE_ENTERPRISE_YEARLY_PRICE_ID,
            }

            price_id = price_ids.get((plan, interval))
            if not price_id:
                logger.error(f"No price ID configured for plan: {plan}")
                return None

            # Create checkout session
            session = self._stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                mode="subscription",
                success_url=f"{os.getenv('HOST_SERVER', 'http://localhost:5000')}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{os.getenv('HOST_SERVER', 'http://localhost:5000')}/pricing",
                customer_update={
                    "address": "auto",
                },
            )

            logger.info(f"Created checkout session {session.id} for user {user_id} plan {plan}")
            return session.url
        except Exception as e:
            logger.error(f"Failed to create checkout session: {e}")
            return None

    def handle_webhook(self, payload: bytes, sig_header: str) -> bool:
        """Handle Stripe webhook events.

        Returns True if handled successfully, False otherwise.
        """
        if not self.is_available():
            logger.warning("Stripe not available for webhook handling")
            return False

        if not STRIPE_WEBHOOK_SECRET:
            logger.warning("STRIPE_WEBHOOK_SECRET not configured — webhooks disabled")
            return False

        try:
            event = self._stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)

            logger.info(f"Received Stripe webhook: {event.type}")

            if event.type == "customer.subscription.created":
                self._activate_subscription(event.data.object)
            elif event.type == "customer.subscription.updated":
                self._update_subscription(event.data.object)
            elif event.type == "customer.subscription.deleted":
                self._deactivate_subscription(event.data.object)
            elif event.type == "invoice.payment_failed":
                self._handle_payment_failure(event.data.object)
            elif event.type == "invoice.payment_succeeded":
                self._handle_payment_success(event.data.object)
            else:
                logger.info(f"Unhandled webhook event type: {event.type}")

            return True
        except Exception as e:
            logger.error(f"Failed to handle webhook: {e}")
            return False

    def _activate_subscription(self, subscription):
        """Activate user's subscription when payment succeeds."""
        try:
            customer_id = subscription.customer
            user_id = subscription.metadata.get("user_id")

            if not user_id:
                # Try to get user_id from customer metadata
                customer = self._stripe.Customer.retrieve(customer_id)
                user_id = customer.metadata.get("user_id")

            if user_id:
                from database.user_db import User, db_session
                from datetime import datetime, timedelta, timezone

                user = User.query.get(int(user_id))
                if user:
                    # Determine plan from the price ID used in the subscription
                    # Determine plan from the price ID used in the subscription
                    items = subscription.get("items", {})
                    items_data = (
                        items.get("data", [])
                        if isinstance(items, dict)
                        else (items.data if hasattr(items, "data") else [])
                    )
                    price_id = items_data[0].price.id if items_data else None
                    plan = PRICE_ID_TO_PLAN.get(price_id, "pro")

                    user.plan = plan
                    # Set expiry based on billing interval (use subscription's current period end)
                    period_end = subscription.get("current_period_end")
                    if period_end:
                        user.plan_expires_at = datetime.fromtimestamp(period_end, tz=timezone.utc)
                    else:
                        user.plan_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
                    db_session.commit()

                    logger.info(
                        f"Activated {plan} subscription for user {user_id} (price: {price_id})"
                    )
        except Exception as e:
            logger.error(f"Failed to activate subscription: {e}")

    def _deactivate_subscription(self, subscription):
        """Deactivate user's subscription when cancelled."""
        try:
            customer_id = subscription.customer
            user_id = subscription.metadata.get("user_id")

            if not user_id:
                customer = self._stripe.Customer.retrieve(customer_id)
                user_id = customer.metadata.get("user_id")

            if user_id:
                from database.user_db import User, db_session

                user = User.query.get(int(user_id))
                if user:
                    user.plan = "free"
                    user.plan_expires_at = None
                    db_session.commit()

                    logger.info(f"Deactivated subscription for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to deactivate subscription: {e}")

    def _update_subscription(self, subscription):
        """Handle subscription updates (plan changes)."""
        logger.info(f"Subscription updated: {subscription.id}")
        # TODO: Handle plan upgrades/downgrades

    def _handle_payment_failure(self, invoice):
        """Handle payment failure - send notification, start grace period."""
        logger.warning(f"Payment failed for invoice {invoice.id}")
        # TODO: Send email notification, start 7-day grace period

    def _handle_payment_success(self, invoice):
        """Handle successful payment - extend subscription."""
        logger.info(f"Payment succeeded for invoice {invoice.id}")
        # TODO: Extend subscription end date

    def create_customer_portal_session(self, user_id: int) -> Optional[str]:
        """Create Stripe Customer Portal URL for subscription management.

        Returns portal URL or None if failed.
        """
        if not self.is_available():
            return None

        try:
            from database.user_db import User

            user = User.query.get(user_id)
            if not user or not user.stripe_customer_id:
                return None

            session = self._stripe.billing_portal.Session.create(
                customer=user.stripe_customer_id,
                return_url=f"{os.getenv('HOST_SERVER', 'http://localhost:5000')}/billing",
            )

            return session.url
        except Exception as e:
            logger.error(f"Failed to create portal session: {e}")
            return None


# Global billing service instance
billing_service = BillingService()
