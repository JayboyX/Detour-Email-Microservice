"""
Subscription Service
"""

import uuid
from datetime import datetime
from decimal import Decimal

from app.shared.database import database_service
from app.wallet.service import wallet_service
from app.email.service import email_service
from .utils import get_next_friday


class SubscriptionService:

    # ---------------------------------------------------------
    # Active Subscription Lookup
    # ---------------------------------------------------------
    def get_active_subscription(self, user_id: str):
        result = database_service.supabase.make_request(
            method="GET",
            endpoint=f"/rest/v1/user_subscriptions?user_id=eq.{user_id}&is_active=eq.true",
            headers=database_service.supabase.service_headers,
        )
        return result[0] if result else None

    # ---------------------------------------------------------
    # Package Lookup
    # ---------------------------------------------------------
    def get_package(self, package_id: str):
        pkg = database_service.supabase.make_request(
            method="GET",
            endpoint=f"/rest/v1/subscription_packages?id=eq.{package_id}",
            headers=database_service.supabase.service_headers,
        )
        return pkg[0] if pkg else None

    # ---------------------------------------------------------
    # Create Package
    # ---------------------------------------------------------
    def create_package(self, req):
        data = {
            "id": str(uuid.uuid4()),
            "name": req.name,
            "price": req.price,
            "period": req.period,
            "description": req.description,
            "benefits": req.benefits,
            "weekly_advance_limit": req.weekly_advance_limit,
            "advance_percentage": req.advance_percentage,
            "auto_repay_rate": req.auto_repay_rate,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        saved = database_service.supabase.make_request(
            method="POST",
            endpoint="/rest/v1/subscription_packages",
            data=data,
            headers=database_service.supabase.service_headers,
        )

        return {
            "success": True,
            "message": "Subscription package created",
            "data": saved[0],
        }

    # ---------------------------------------------------------
    # Activate Subscription
    # ---------------------------------------------------------
    def activate_subscription(self, user_id: str, package_id: str):
        existing = self.get_active_subscription(user_id)
        if existing:
            return {"success": False, "message": "User already has an active subscription"}

        pkg = self.get_package(package_id)
        if not pkg:
            return {"success": False, "message": "Subscription package not found"}

        price = float(pkg["price"])

        wallet = wallet_service.get_wallet_by_user_id(user_id)
        if not wallet:
            return {"success": False, "message": "Wallet not found"}

        if float(wallet["balance"]) < price:
            return {"success": False, "message": "Insufficient wallet balance"}

        deduction = wallet_service.withdraw_funds(
            wallet_id=wallet["id"],
            amount=price,
            description=f"Initial subscription payment for {pkg['name']}",
        )
        if not deduction["success"]:
            return {"success": False, "message": "Initial payment failed"}

        self.add_to_revenue(price)

        subscription_row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "package_id": package_id,
            "is_active": True,
            "start_date": datetime.utcnow().date().isoformat(),
            "renewal_period": "weekly",
            "current_weekly_price": price,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        saved_sub = database_service.supabase.make_request(
            method="POST",
            endpoint="/rest/v1/user_subscriptions",
            data=subscription_row,
            headers=database_service.supabase.service_headers,
        )

        self.log_event(user_id, package_id, "activated")
        self.log_event(user_id, package_id, "initial_payment", {"amount": price})
        self.send_confirmation_email(user_id, pkg)

        return {"success": True, "message": "Subscription activated", "data": saved_sub[0]}

    # ---------------------------------------------------------
    # Cancel Subscription
    # ---------------------------------------------------------
    def cancel_subscription(self, user_id: str, reason: str = None):
        sub = self.get_active_subscription(user_id)
        if not sub:
            return {"success": False, "message": "No active subscription to cancel"}

        update = {
            "is_active": False,
            "cancelled_at": datetime.utcnow().isoformat(),
            "cancellation_reason": reason,
            "updated_at": datetime.utcnow().isoformat(),
        }

        database_service.supabase.make_request(
            method="PATCH",
            endpoint=f"/rest/v1/user_subscriptions?id=eq.{sub['id']}",
            data=update,
            headers=database_service.supabase.service_headers,
        )

        self.log_event(user_id, sub["package_id"], "cancelled", {"reason": reason})

        return {"success": True, "message": "Subscription cancelled"}

    # ---------------------------------------------------------
    # Weekly Billing (Cron)
    # ---------------------------------------------------------
    def bill_all_users(self):
        subs = database_service.supabase.make_request(
            method="GET",
            endpoint="/rest/v1/user_subscriptions?is_active=eq.true",
            headers=database_service.supabase.service_headers,
        )

        results = []

        for sub in subs:
            user_id = sub["user_id"]
            package_id = sub["package_id"]
            amount = float(sub["current_weekly_price"])

            wallet = wallet_service.get_wallet_by_user_id(user_id)
            if not wallet:
                results.append({"user_id": user_id, "status": "missing_wallet"})
                continue

            if float(wallet["balance"]) >= amount:
                withdrawal = wallet_service.withdraw_funds(
                    wallet_id=wallet["id"],
                    amount=amount,
                    description="Weekly subscription renewal",
                )

                if withdrawal["success"]:
                    self.add_to_revenue(amount)
                    self.log_event(user_id, package_id, "weekly_deduction", {"amount": amount})
                    results.append({"user_id": user_id, "status": "charged"})
                else:
                    self.log_event(user_id, package_id, "failed_payment")
                    results.append({"user_id": user_id, "status": "deduction_failed"})

            else:
                self.log_event(user_id, package_id, "failed_payment", {"reason": "insufficient_funds"})
                results.append({"user_id": user_id, "status": "insufficient_funds"})

        return results

    # ---------------------------------------------------------
    # Event Logging
    # ---------------------------------------------------------
    def log_event(self, user_id, package_id, event_type, metadata=None):
        event = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "package_id": package_id,
            "event_type": event_type,
            "metadata": metadata,
            "created_at": datetime.utcnow().isoformat(),
        }

        database_service.supabase.make_request(
            method="POST",
            endpoint="/rest/v1/subscription_events",
            data=event,
            headers=database_service.supabase.service_headers,
        )

    # ---------------------------------------------------------
    # Revenue Pool
    # ---------------------------------------------------------
    def add_to_revenue(self, amount: float):
        pool = database_service.supabase.make_request(
            method="GET",
            endpoint="/rest/v1/detour_revenue_pool?limit=1",
            headers=database_service.supabase.service_headers,
        )

        if not pool:
            return

        pool = pool[0]
        new_total = float(pool["total_collected"]) + amount

        database_service.supabase.make_request(
            method="PATCH",
            endpoint=f"/rest/v1/detour_revenue_pool?id=eq.{pool['id']}",
            data={
                "total_collected": new_total,
                "last_updated": datetime.utcnow().isoformat(),
            },
            headers=database_service.supabase.service_headers,
        )

    # ---------------------------------------------------------
    # Confirmation Email
    # ---------------------------------------------------------
    def send_confirmation_email(self, user_id: str, pkg):
        user = database_service.get_user_by_id(user_id)
        if not user:
            return

        name = user["full_name"]
        email = user["email"]
        benefits = pkg.get("benefits", []) or []

        subject = f"Your {pkg['name']} Subscription is Active!"

        body = f"""
        <h2>Subscription Activated</h2>
        <p>Hello {name},</p>
        <p>You have successfully subscribed to <strong>{pkg['name']}</strong>.</p>
        <p><strong>Weekly Price:</strong> R {pkg['price']}</p>
        <p><strong>Next Billing:</strong> Coming Friday at Midnight</p>
        <p><strong>Your Benefits:</strong></p>
        <ul>{''.join(f'<li>{b}</li>' for b in benefits)}</ul>
        <p>Thank you for being a Detour driver! 🚗💚</p>
        """

        email_service.send_email(
            to=email,
            subject=subject,
            html_content=body,
        )


subscription_service = SubscriptionService()
