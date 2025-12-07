from decimal import Decimal
from app.shared.database import database_service
from app.transactions.service import transactions_service
from app.buying.utils import now_iso


class BuyingService:

    # ------------------------------------------------
    # Load bundle info
    # ------------------------------------------------
    def get_bundle(self, bundle_id):
        endpoint = f"/rest/v1/bundle_catalog?id=eq.{bundle_id}"
        bundle = database_service.supabase.make_request(
            "GET",
            endpoint,
            headers=database_service.supabase.anon_headers
        )
        return bundle[0] if bundle else None

    # ------------------------------------------------
    # Log purchase attempt (pending / failed / completed)
    # ------------------------------------------------
    def log_purchase(self, user_id, number, type, network, amount, product_id, status, metadata=None):

        entry = {
            "user_id": user_id,
            "beneficiary_number": number,
            "type": type,
            "network": network,
            "amount": float(amount),
            "product_id": product_id,
            "status": status,
            "metadata": metadata or {},
            "created_at": now_iso()
        }

        database_service.supabase.make_request(
            "POST",
            "/rest/v1/purchase_history",
            entry,
            database_service.supabase.service_headers
        )

    # ------------------------------------------------
    # PURCHASE AIRTIME
    # ------------------------------------------------
    def buy_airtime(self, req):

        # Log pending
        self.log_purchase(
            req.user_id,
            req.beneficiary_number,
            "airtime",
            req.network,
            float(req.amount),
            None,
            "pending"
        )

        # Deduct from wallet using the Transactions Microservice
        result = transactions_service.process_payment(type(
            "obj", (object,), {
                "user_id": req.user_id,
                "amount": req.amount,
                "payment_type": "airtime",
                "description": f"Airtime purchase for {req.beneficiary_number}",
                "metadata": {"network": req.network}
            }
        ))

        if not result["success"]:
            self.log_purchase(
                req.user_id,
                req.beneficiary_number,
                "airtime",
                req.network,
                float(req.amount),
                None,
                "failed"
            )
            return result

        # Log success
        self.log_purchase(
            req.user_id,
            req.beneficiary_number,
            "airtime",
            req.network,
            float(req.amount),
            None,
            "completed",
            metadata={"reference": result["transaction"]["reference"]}
        )

        return {
            "success": True,
            "message": "Airtime purchase successful",
            "transaction": result["transaction"],
            "new_balance": result["new_balance"]
        }

    # ------------------------------------------------
    # PURCHASE BUNDLE (DATA / VOICE)
    # ------------------------------------------------
    def buy_bundle(self, req):

        bundle = self.get_bundle(req.bundle_id)
        if not bundle:
            return {"success": False, "message": "Bundle not found"}

        # Log pending
        self.log_purchase(
            req.user_id,
            req.beneficiary_number,
            bundle["type"],
            bundle["network"],
            float(bundle["price"]),
            bundle["id"],
            "pending",
            metadata=bundle
        )

        # Deduct from Wallet
        result = transactions_service.process_payment(type(
            "obj", (object,), {
                "user_id": req.user_id,
                "amount": Decimal(bundle["price"]),
                "payment_type": "bundle_purchase",
                "description": f"{bundle['name']} for {req.beneficiary_number}",
                "metadata": {"bundle_id": bundle["id"]}
            }
        ))

        if not result["success"]:
            self.log_purchase(
                req.user_id,
                req.beneficiary_number,
                bundle["type"],
                bundle["network"],
                float(bundle["price"]),
                bundle["id"],
                "failed"
            )
            return result

        # Log success
        self.log_purchase(
            req.user_id,
            req.beneficiary_number,
            bundle["type"],
            bundle["network"],
            float(bundle["price"]),
            bundle["id"],
            "completed",
            metadata=bundle
        )

        return {
            "success": True,
            "message": "Bundle purchase successful",
            "transaction": result["transaction"],
            "new_balance": result["new_balance"]
        }


# SINGLETON INSTANCE
buying_service = BuyingService()
