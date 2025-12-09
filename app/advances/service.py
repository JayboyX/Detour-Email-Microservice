from decimal import Decimal
from datetime import datetime
from app.shared.database import database_service
from app.wallet.service import wallet_service
from app.transactions.service import transactions_service
from app.subscriptions.service import subscription_service
from app.advances.utils import now_iso, calculate_repay_amount, weeks_since


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
            "subscription_price": float(pkg["price"]),
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
    # FULL AVAILABLE ADVANCE CALCULATION
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

        # Remaining from weekly package limit
        limit_remaining = max(0, weekly_limit - used)

        # Wallet factor * performance percentage
        wallet = wallet_service.get_wallet_by_user_id(user_id)
        wallet_balance = float(wallet["balance"]) if wallet else 0

        performance_limit = wallet_balance * (percentage / 100)

        # Final available = min(package_limit_remaining, wallet_performance)
        available = min(limit_remaining, performance_limit)

        return {
            "weekly_limit": weekly_limit,
            "used": used,
            "performance_limit": round(performance_limit, 2),
            "available": round(available, 2),
        }

    # ------------------------------------------------------
    # REQUEST ADVANCE — simple eligibility
    # ------------------------------------------------------
    def request_advance(self, req):
        limits, error = self.get_user_limits(req.user_id)
        if error:
            return error

        outstanding = self.get_outstanding(req.user_id)
        used = sum(float(x["outstanding_amount"]) for x in outstanding)

        if used + float(req.amount) > limits["weekly_limit"]:
            return {
                "success": False,
                "message": f"Advance limit exceeded. Remaining available: {limits['weekly_limit'] - used}"
            }

        return {
            "success": True,
            "message": "Advance allowed",
            "available_remaining": limits["weekly_limit"] - used
        }

    # ------------------------------------------------------
    # APPROVE ADVANCE
    # ------------------------------------------------------
    def approve_advance(self, req):

        pool_res = database_service.supabase.make_request(
            "GET",
            f"/rest/v1/advance_issuer_pool?id=eq.{req.issuer_pool_id}",
            headers=database_service.supabase.anon_headers
        )

        if not pool_res:
            return {"success": False, "message": "Issuer pool not found"}

        pool = pool_res[0]
        if float(pool["current_balance"]) < float(req.amount):
            return {"success": False, "message": "Issuer pool insufficient"}

        # 1. CREDIT WALLET
        credit = transactions_service.process_credit(type(
            "obj", (object,), {
                "user_id": req.user_id,
                "amount": req.amount,
                "credit_type": "advance_credit",
                "description": "Advance credited to wallet",
                "reference": getattr(req, "reference", None),
                "metadata": {"issuer_pool_id": req.issuer_pool_id}
            }
        ))


        if not credit["success"]:
            return credit

        # 2. UPDATE POOL
        database_service.supabase.make_request(
            "PATCH",
            f"/rest/v1/advance_issuer_pool?id=eq.{pool['id']}",
            {
                "current_balance": float(pool["current_balance"]) - float(req.amount),
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
    # WEEKLY SUBSCRIPTION FEE COLLECTION
    # ------------------------------------------------------
    def collect_subscription_fee(self, user_id, fee_amount):

        debit = transactions_service.process_payment(type(
            "obj", (object,), {
                "user_id": user_id,
                "amount": Decimal(fee_amount),
                "payment_type": "subscription_weekly_fee",
                "description": "Weekly subscription fee",
                "metadata": {}
            }
        ))

        if not debit["success"]:
            return {"success": False, "message": "Insufficient wallet funds"}

        # Push to Detour revenue pool
        pool = database_service.supabase.make_request(
            "GET",
            "/rest/v1/detour_revenue_pool",
            headers=database_service.supabase.anon_headers
        )[0]

        updated_total = float(pool["total_collected"]) + float(fee_amount)

        database_service.supabase.make_request(
            "PATCH",
            f"/rest/v1/detour_revenue_pool?id=eq.{pool['id']}",
            {
                "total_collected": updated_total,
                "last_updated": now_iso()
            },
            database_service.supabase.service_headers
        )

        return {"success": True}

    # ------------------------------------------------------
    # AUTO REPAY + SUBSCRIPTION FEE
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
            subscription_fee = limits["subscription_price"]

            # STEP 1: Subscription fee
            self.collect_subscription_fee(user_id, subscription_fee)

            wallet = wallet_service.get_wallet_by_user_id(user_id)
            if not wallet:
                continue

            wallet_balance = float(wallet["balance"])
            if wallet_balance <= 0:
                continue

            # STEP 2: Compute repayment amount
            standard_repay = wallet_balance * (repay_rate / 100)

            age_weeks = weeks_since(adv["created_at"])
            weeks_left = max(1, 4 - age_weeks)

            required_repay = outstanding / weeks_left

            repay_amount = min(max(standard_repay, required_repay), outstanding)

            # STEP 3: Process repayment
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

            # STEP 4: Return repayment to issuer pool
            pool = database_service.supabase.make_request(
                "GET",
                f"/rest/v1/advance_issuer_pool?id=eq.{adv['issuer_pool_id']}",
                headers=database_service.supabase.anon_headers
            )[0]

            database_service.supabase.make_request(
                "PATCH",
                f"/rest/v1/advance_issuer_pool?id=eq.{pool['id']}",
                {
                    "current_balance": float(pool["current_balance"]) + repay_amount,
                    "total_repaid": float(pool["total_repaid"]) + repay_amount
                },
                database_service.supabase.service_headers
            )

            # Log repayment
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
            "message": "Auto repayment + subscription fee cycle completed",
            "processed": processed
        }
    
def get_true_earnings(self, user_id):
    """Return total earnings excluding advance credits."""
    
    wallet = wallet_service.get_wallet_by_user_id(user_id)
    if not wallet:
        return 0

    wallet_id = wallet["id"]

    # Fetch all DEPOSITS
    txs = database_service.supabase.make_request(
        "GET",
        f"/rest/v1/wallet_transactions?wallet_id=eq.{wallet_id}&transaction_type=eq.deposit",
        headers=database_service.supabase.anon_headers
    ) or []

    total_deposits = 0
    total_advance_credits = 0

    for tx in txs:
        amount = float(tx.get("amount", 0))

        # Check if this deposit is an advance credit
        meta = tx.get("metadata", {})
        credit_type = meta.get("credit_type")

        if credit_type == "advance_credit":
            total_advance_credits += amount
        else:
            total_deposits += amount

    # True earnings = all deposits except advance credits
    return total_deposits



advances_service = AdvancesService()
