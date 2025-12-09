from decimal import Decimal
from datetime import datetime
from app.shared.database import database_service
from app.wallet.service import wallet_service
from app.transactions.service import transactions_service
from app.subscriptions.service import subscription_service
from app.advances.utils import now_iso, weeks_since


class AdvancesService:

    # ------------------------------------------------------
    # Get ACTIVE subscription & limits
    # ------------------------------------------------------
    def get_user_limits(self, user_id):
        sub = subscription_service.get_active_subscription(user_id)
        if not sub:
            return None, {"success": False, "message": "User has no active subscription"}

        pkg = subscription_service.get_package(sub["package_id"])

        return {
            "weekly_limit": float(pkg["weekly_advance_limit"]),
            "repay_rate": int(pkg["auto_repay_rate"]),
            "advance_percentage": int(pkg["advance_percentage"]),
        }, None


    # ------------------------------------------------------
    # Get outstanding active advances
    # ------------------------------------------------------
    def get_outstanding(self, user_id):
        endpoint = f"/rest/v1/user_advances?user_id=eq.{user_id}&status=eq.active"
        result = database_service.supabase.make_request(
            "GET", endpoint, headers=database_service.supabase.anon_headers
        )
        return result or []


    # ------------------------------------------------------
    # Compute full availability for UI + logic
    # ------------------------------------------------------
    def get_available_advance(self, user_id):

        limits, error = self.get_user_limits(user_id)
        if error:
            return {
                "weekly_limit": 0,
                "used": 0,
                "performance_limit": 0,
                "available": 0
            }

        weekly_limit = limits["weekly_limit"]
        percentage = limits["advance_percentage"]

        outstanding = self.get_outstanding(user_id)
        used = sum(float(x.get("outstanding_amount", 0)) for x in outstanding)

        # Remaining weekly package limit
        limit_remaining = max(0, weekly_limit - used)

        # Wallet performance limit
        wallet = wallet_service.get_wallet_by_user_id(user_id)
        wallet_balance = float(wallet["balance"]) if wallet else 0
        performance_limit = wallet_balance * (percentage / 100)

        # Issuer pool limit
        pool = self.get_issuer_pool()
        pool_limit = float(pool["current_balance"])

        # FINAL AVAILABLE
        available = max(0, min(limit_remaining, performance_limit, pool_limit))

        return {
            "weekly_limit": weekly_limit,
            "used": used,
            "performance_limit": round(performance_limit, 2),
            "pool_limit": pool_limit,
            "available": round(available, 2),
        }


    # ------------------------------------------------------
    # Internal: Fetch issuer pool (single pool model)
    # ------------------------------------------------------
    def get_issuer_pool(self):
        res = database_service.supabase.make_request(
            "GET",
            "/rest/v1/advance_issuer_pool?select=*",
            headers=database_service.supabase.anon_headers
        )
        return res[0]


    # ------------------------------------------------------
    # Fully automatic advance issuing
    # ------------------------------------------------------
    def take_advance(self, req):

        # Step 1 - Get eligibility limits
        limits, error = self.get_user_limits(req.user_id)
        if error:
            return error

        # Step 2 - Compute availability
        availability = self.get_available_advance(req.user_id)
        max_available = float(availability["available"])

        if float(req.amount) > max_available:
            return {
                "success": False,
                "message": f"Requested amount exceeds your available advance. Max available: {max_available}"
            }

        # Step 3 - Check issuer pool has sufficient funds
        pool = self.get_issuer_pool()
        pool_balance = float(pool["current_balance"])

        if pool_balance < float(req.amount):
            return {"success": False, "message": "Issuer pool has insufficient funds"}

        # ------------------------------------------------------
        # ISSUE ADVANCE AUTOMATICALLY
        # ------------------------------------------------------

        # 1. CREDIT WALLET
        credit = transactions_service.process_credit(type(
            "obj", (object,), {
                "user_id": req.user_id,
                "amount": req.amount,
                "credit_type": "advance_credit",
                "description": "Automatic advance credited",
                "metadata": {"issuer_pool_id": pool["id"]}
            }
        ))

        if not credit["success"]:
            return credit

        # 2. UPDATE POOL (deduct lent amount)
        database_service.supabase.make_request(
            "PATCH",
            f"/rest/v1/advance_issuer_pool?id=eq.{pool['id']}",
            {
                "current_balance": pool_balance - float(req.amount),
                "total_lent": float(pool["total_lent"]) + float(req.amount),
                "updated_at": now_iso()
            },
            database_service.supabase.service_headers
        )

        # 3. CREATE USER ADVANCE RECORD
        adv = {
            "user_id": req.user_id,
            "issuer_pool_id": pool["id"],
            "total_amount": float(req.amount),
            "outstanding_amount": float(req.amount),
            "created_at": now_iso()
        }

        created = database_service.supabase.make_request(
            "POST",
            "/rest/v1/user_advances",
            adv,
            database_service.supabase.service_headers
        )

        return {
            "success": True,
            "message": "Advance issued successfully",
            "advance": created[0]
        }


    # ------------------------------------------------------
    # AUTO REPAYMENT ENGINE (weekly cron)
    # ------------------------------------------------------
    def auto_repay(self):

        advances = database_service.supabase.make_request(
            "GET",
            "/rest/v1/user_advances?status=eq.active",
            headers=database_service.supabase.anon_headers
        )

        if not advances:
            return {"success": True, "message": "No advances to process"}

        processed = []

        for adv in advances:
            user_id = adv["user_id"]
            outstanding = float(adv["outstanding_amount"])

            limits, error = self.get_user_limits(user_id)
            if error:
                continue

            repay_rate = limits["repay_rate"]

            wallet = wallet_service.get_wallet_by_user_id(user_id)
            if not wallet:
                continue

            wallet_balance = float(wallet["balance"])
            if wallet_balance <= 0:
                continue

            # Automatic deduction = repay_rate %
            repay_amount = round(wallet_balance * (repay_rate / 100), 2)
            repay_amount = min(repay_amount, outstanding)

            if repay_amount <= 0:
                continue

            # PROCESS PAYMENT
            debit = transactions_service.process_payment(type(
                "obj", (object,), {
                    "user_id": user_id,
                    "amount": Decimal(repay_amount),
                    "payment_type": "advance_repayment",
                    "description": "Automatic advance repayment",
                    "metadata": {"advance_id": adv["id"]}
                }
            ))

            if not debit["success"]:
                continue

            # UPDATE ADVANCE RECORD
            new_outstanding = outstanding - repay_amount
            status = "repaid" if new_outstanding <= 0 else "active"

            database_service.supabase.make_request(
                "PATCH",
                f"/rest/v1/user_advances?id=eq.{adv['id']}",
                {
                    "outstanding_amount": new_outstanding,
                    "status": status,
                    "updated_at": now_iso(),
                    "repaid_at": now_iso() if status == "repaid" else None
                },
                database_service.supabase.service_headers
            )

            # RETURN MONEY TO POOL
            pool = self.get_issuer_pool()
            database_service.supabase.make_request(
                "PATCH",
                f"/rest/v1/advance_issuer_pool?id=eq.{pool['id']}",
                {
                    "current_balance": float(pool["current_balance"]) + repay_amount,
                    "total_repaid": float(pool["total_repaid"]) + repay_amount
                },
                database_service.supabase.service_headers
            )

            # LOG REPAYMENT
            database_service.supabase.make_request(
                "POST",
                "/rest/v1/advance_repayments",
                {
                    "user_id": user_id,
                    "advance_id": adv["id"],
                    "amount": repay_amount
                },
                database_service.supabase.service_headers
            )

            processed.append({
                "user_id": user_id,
                "advance_id": adv["id"],
                "repaid": repay_amount
            })

        return {
            "success": True,
            "message": "Auto repayment cycle completed",
            "processed": processed
        }


advances_service = AdvancesService()
