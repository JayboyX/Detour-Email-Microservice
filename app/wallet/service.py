"""
Wallet Service
"""

import logging
import uuid
import random
import string
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.shared.database import database_service

logger = logging.getLogger(__name__)


class WalletService:
    def __init__(self):
        self.supabase = database_service.supabase

    # ---------------------------------------------------------
    # Creation Utilities
    # ---------------------------------------------------------
    def generate_wallet_number(self) -> str:
        while True:
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            wallet_number = f"WLT-{code}"
            if not self.get_wallet_by_number(wallet_number):
                return wallet_number

    def create_wallet(self, user_id: str) -> Dict[str, Any]:
        try:
            existing = self.get_wallet_by_user_id(user_id)
            if existing:
                return {"success": False, "message": "User already has a wallet", "wallet": existing}

            wallet_number = self.generate_wallet_number()
            data = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "wallet_number": wallet_number,
                "balance": 0.00,
                "currency": "ZAR",
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            response = self.supabase.make_request(
                "POST", "/rest/v1/wallets", data, self.supabase.service_headers
            )

            if response:
                self.log_wallet_creation(user_id, wallet_number)
                self.create_transaction(
                    wallet_id=response[0]["id"],
                    transaction_type="account_opening",
                    amount=0.00,
                    description="Wallet account opened",
                )
                return {"success": True, "message": "Wallet created successfully", "wallet": response[0]}

            return {"success": False, "message": "Failed to create wallet"}

        except Exception as e:
            logger.error(f"Wallet create error: {e}")
            return {"success": False, "message": str(e)}

    # ---------------------------------------------------------
    # Lookup
    # ---------------------------------------------------------
    def get_wallet_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            endpoint = f"/rest/v1/wallets?user_id=eq.{user_id}"
            res = self.supabase.make_request("GET", endpoint, headers=self.supabase.anon_headers)
            return res[0] if res else None
        except Exception as e:
            logger.error(f"Wallet lookup error: {e}")
            return None

    def get_wallet_by_number(self, wallet_number: str):
        try:
            endpoint = f"/rest/v1/wallets?wallet_number=eq.{wallet_number}"
            res = self.supabase.make_request("GET", endpoint, headers=self.supabase.anon_headers)
            return res[0] if res else None
        except Exception as e:
            logger.error(f"Wallet number lookup error: {e}")
            return None

    def get_wallet_by_id(self, wallet_id: str):
        try:
            endpoint = f"/rest/v1/wallets?id=eq.{wallet_id}"
            res = self.supabase.make_request("GET", endpoint, headers=self.supabase.anon_headers)
            return res[0] if res else None
        except Exception as e:
            logger.error(f"Wallet ID lookup error: {e}")
            return None

    # ---------------------------------------------------------
    # Balance & Transaction Handling
    # ---------------------------------------------------------
    def update_wallet_balance(self, wallet_id: str, amount: float, transaction_type: str) -> Dict[str, Any]:
        try:
            wallet = self.get_wallet_by_id(wallet_id)
            if not wallet:
                return {"success": False, "message": "Wallet not found"}

            new_balance = float(wallet["balance"]) + amount

            if new_balance < 0 and transaction_type not in ["credit", "refund"]:
                return {"success": False, "message": "Insufficient funds"}

            updates = {
                "balance": new_balance,
                "updated_at": datetime.utcnow().isoformat(),
                "last_transaction_at": datetime.utcnow().isoformat(),
            }

            endpoint = f"/rest/v1/wallets?id=eq.{wallet_id}"
            response = self.supabase.make_request(
                "PATCH", endpoint, updates, self.supabase.service_headers
            )

            if response:
                return {
                    "success": True,
                    "message": "Balance updated",
                    "new_balance": new_balance,
                    "wallet": response[0],
                }

            return {"success": False, "message": "Failed to update balance"}

        except Exception as e:
            logger.error(f"Balance update error: {e}")
            return {"success": False, "message": str(e)}

    def create_transaction(
        self,
        wallet_id: str,
        transaction_type: str,
        amount: float,
        description: str = "",
        reference: str = "",
        metadata: Dict = None,
    ):
        try:
            status_map = {
                "deposit": "completed",
                "withdrawal": "pending",
                "transfer": "pending",
                "payment": "pending",
                "refund": "completed",
                "account_opening": "completed",
            }

            tx = {
                "id": str(uuid.uuid4()),
                "wallet_id": wallet_id,
                "transaction_type": transaction_type,
                "amount": amount,
                "currency": "ZAR",
                "reference": reference or f"TX-{str(uuid.uuid4())[:8].upper()}",
                "description": description,
                "status": status_map.get(transaction_type, "pending"),
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat(),
            }

            response = self.supabase.make_request(
                "POST", "/rest/v1/wallet_transactions", tx, self.supabase.service_headers
            )

            if response:
                return {"success": True, "message": "Transaction created", "transaction": response[0]}

            return {"success": False, "message": "Failed to create transaction"}

        except Exception as e:
            logger.error(f"Transaction error: {e}")
            return {"success": False, "message": str(e)}

    # ---------------------------------------------------------
    # History
    # ---------------------------------------------------------
    def get_transactions(self, wallet_id: str, limit=50, offset=0):
        try:
            endpoint = f"/rest/v1/wallet_transactions?wallet_id=eq.{wallet_id}&order=created_at.desc&limit={limit}&offset={offset}"
            res = self.supabase.make_request("GET", endpoint, headers=self.supabase.anon_headers)
            return res or []
        except Exception as e:
            logger.error(f"Transaction fetch error: {e}")
            return []

    # ---------------------------------------------------------
    # Audit Logging
    # ---------------------------------------------------------
    def log_wallet_creation(self, user_id: str, wallet_number: str):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "wallet_number": wallet_number,
            "event": "wallet_created",
        }
        try:
            with open("logs/wallet_creation.log", "a") as f:
                import json
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Wallet creation log error: {e}")


wallet_service = WalletService()
