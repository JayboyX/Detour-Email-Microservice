from decimal import Decimal
from datetime import datetime
from app.shared.database import database_service
from app.wallet.service import wallet_service
from app.transactions.service import transactions_service
from app.subscriptions.service import subscription_service
from app.advances.utils import now_iso


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
        }, None


    # ------------------------------------------------------
    # Get outstanding advances for user
    # ------------------------------------------------------
    def get_outstanding(self, user_id):
        endpoint = f"/rest/v1/user_advances?user_id=eq.{user_id}&status=eq.active"
        result = database_service.supabase.make_request(
            "GET", endpoint, headers=database_service.supabase.anon_headers
        )
        return result or []


    # ------------------------------------------------------
    # Compute true available advance (correct business rules)
    # ------------------------------------------------------
    def get_available_advance(self, user_id):

        limits, error = self.get_user_limits(user_id)
        if error:
            return {
                "weekly_limit": 0,
                "outstanding": 0,
                "available": 0,
                "pool_limit": 0
            }

        weekly_limit = limits["weekly_limit"]

        outstanding = self.get_outstanding(user_id)
        total_outstanding = sum(float(x["outstanding_amount"]) for x in outstanding)

        # RULE 1 — If customer owes ANYTHING, they cannot borrow again.
        if total_outstanding > 0:
            return {
                "weekly_limit": weekly_limit,
                "outstanding": total_outstanding,
                "available": 0,
                "pool_limit": 0
            }

        # RULE 2 — If no outstanding debt, user gets full weekly limit.
        pool = self.get_issuer_pool()
        pool_balance = float(pool["current_balance"])

        available = min(weekly_limit, pool_balance)

        return {
            "weekly_limit": weekly_limit,
            "outstanding": 0,
            "available": available,
            "pool_limit": pool_balance,
        }


    # ------------------------------------------------------
    # Internal: Get single issuer pool
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

        limits, error = self.get_user_limits(req.user_id)
        if error:
            return error

        availability = self.get_available_advance(req.user_id)
        max_available = float(availability["available"])

        # DO NOT ALLOW BORROWING IF ANY OUTSTANDING EXISTS
        if float(availability["outstanding"]) > 0:
            return {
                "success": False,
                "message": "You must repay your existing advance before taking another."
            }

        # Ensure amount does not exceed available
        if float(req.amount) > max_available:
            return {
                "success": False,
                "message": f"Requested amount exceeds your available limit. Max available: {max_available}"
            }

        # Verify pool liquidity
        pool = self.get_issuer_pool()
        pool_balance = float(pool["current_balance"])
        if pool_balance < float(req.amount):
            return {"success": False, "message": "Issuer pool has insufficient funds"}

        # ------------------------------------------------------
        # ISSUE ADVANCE
        # ------------------------------------------------------

        # 1. CREDIT WALLET
        credit = transactions_service.process_credit(type(
            "obj", (object,), {
                "user_id": req.user_id,
                "amount": req.amount,
                "credit_type": "advance_credit",
                "description": "Advance credited",
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

        # 3. CREATE ADVANCE RECORD
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
    # AUTOMATIC WEEKLY REPAYMENT (CORRECT LOGIC)
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
            total_amount = float(adv["total_amount"])

            limits, error = self.get_user_limits(user_id)
            if error:
                continue

            repay_rate = limits["repay_rate"]

            # ------------------------------------------------------
            # CORRECT REPAYMENT FORMULA:
            # weekly_repay = original amount * repay_rate%
            # ------------------------------------------------------
            weekly_repay = total_amount * (repay_rate / 100)
            repay_amount = min(weekly_repay, outstanding)

            # Check if wallet has the money
            wallet = wallet_service.get_wallet_by_user_id(user_id)
            if not wallet:
                continue

            wallet_balance = float(wallet["balance"])
            if wallet_balance < repay_amount:
                continue  # cannot repay this week

            # PROCESS WALLET PAYMENT
            debit = transactions_service.process_payment(type(
                "obj", (object,), {
                    "user_id": user_id,
                    "amount": Decimal(repay_amount),
                    "payment_type": "advance_repayment",
                    "description": "Weekly automatic repayment",
                    "metadata": {"advance_id": adv["id"]}
                }
            ))

            if not debit["success"]:
                continue

            # UPDATE OUTSTANDING BALANCE
            new_outstanding = outstanding - repay_amount
            repaid_status = "repaid" if new_outstanding <= 0 else "active"

            database_service.supabase.make_request(
                "PATCH",
                f"/rest/v1/user_advances?id=eq.{adv['id']}",
                {
                    "outstanding_amount": new_outstanding,
                    "status": repaid_status,
                    "updated_at": now_iso(),
                    "repaid_at": now_iso() if repaid_status == "repaid" else None
                },
                database_service.supabase.service_headers
            )

            # MONEY RETURNS TO ISSUER POOL
            pool = self.get_issuer_pool()
            new_pool_balance = float(pool["current_balance"]) + repay_amount

            database_service.supabase.make_request(
                "PATCH",
                f"/rest/v1/advance_issuer_pool?id=eq.{pool['id']}",
                {
                    "current_balance": new_pool_balance,
                    "total_repaid": float(pool["total_repaid"]) + repay_amount,
                },
                database_service.supabase.service_headers
            )

            # LOG REPAYMENT ENTRY
            database_service.supabase.make_request(
                "POST",
                "/rest/v1/advance_repayments",
                {
                    "user_id": user_id,
                    "advance_id": adv["id"],
                    "amount": repay_amount,
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
            "message": "Weekly repayment cycle completed",
            "processed": processed
        }


advances_service = AdvancesService()
