"""
Wallet Service - Updated for Correct Credit/Debit Handling
"""

import logging
import uuid
import random
import string
from datetime import datetime
from typing import Optional, Dict, Any

from app.shared.database import database_service

logger = logging.getLogger(__name__)


class WalletService:
    def __init__(self):
        self.supabase = database_service.supabase

    # ---------------------------------------------------------
    # Wallet Creation
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

            res = self.supabase.make_request("POST", "/rest/v1/wallets", data, self.supabase.service_headers)
            if not res:
                return {"success": False, "message": "Failed to create wallet"}

            wallet_id = res[0]["id"]

            # Log account opening
            self.create_transaction(
                wallet_id=wallet_id,
                transaction_type="account_opening",
                amount=0.00,
                description="Wallet account opened",
            )

            return {"success": True, "message": "Wallet created", "wallet": res[0]}

        except Exception as e:
            logger.error(f"Wallet creation error: {e}")
            return {"success": False, "message": str(e)}

    # ---------------------------------------------------------
    # Lookup
    # ---------------------------------------------------------
    def get_wallet_by_user_id(self, user_id: str):
        try:
            res = self.supabase.make_request(
                "GET",
                f"/rest/v1/wallets?user_id=eq.{user_id}",
                headers=self.supabase.anon_headers,
            )
            return res[0] if res else None
        except:
            return None

    def get_wallet_by_id(self, wallet_id: str):
        try:
            res = self.supabase.make_request(
                "GET",
                f"/rest/v1/wallets?id=eq.{wallet_id}",
                headers=self.supabase.anon_headers,
            )
            return res[0] if res else None
        except:
            return None

    def get_wallet_by_number(self, wallet_number: str):
        try:
            res = self.supabase.make_request(
                "GET",
                f"/rest/v1/wallets?wallet_number=eq.{wallet_number}",
                headers=self.supabase.anon_headers,
            )
            return res[0] if res else None
        except:
            return None

    # ---------------------------------------------------------
    # Balance Update (Unified Deposit / Withdrawal)
    # ---------------------------------------------------------
    def update_wallet_balance(self, wallet_id: str, amount: float, transaction_type: str):
        """
        amount > 0  => credit
        amount < 0  => debit
        """

        wallet = self.get_wallet_by_id(wallet_id)
        if not wallet:
            return {"success": False, "message": "Wallet not found"}

        new_balance = float(wallet["balance"]) + amount

        # Prevent negative balances unless it's a credit/refund
        if new_balance < 0:
            return {"success": False, "message": "Insufficient funds"}

        updates = {
            "balance": new_balance,
            "updated_at": datetime.utcnow().isoformat(),
            "last_transaction_at": datetime.utcnow().isoformat(),
        }

        res = self.supabase.make_request(
            "PATCH",
            f"/rest/v1/wallets?id=eq.{wallet_id}",
            updates,
            self.supabase.service_headers,
        )

        if not res:
            return {"success": False, "message": "Failed to update balance"}

        return {"success": True, "new_balance": new_balance, "wallet": res[0]}

    # ---------------------------------------------------------
    # Transaction Logging
    # ---------------------------------------------------------
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
            tx = {
                "id": str(uuid.uuid4()),
                "wallet_id": wallet_id,
                "transaction_type": transaction_type,
                "amount": amount,
                "currency": "ZAR",
                "reference": reference or f"TX-{str(uuid.uuid4())[:8].upper()}",
                "description": description,
                "status": "completed",
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat(),
            }

            res = self.supabase.make_request(
                "POST",
                "/rest/v1/wallet_transactions",
                tx,
                self.supabase.service_headers,
            )

            if not res:
                return {"success": False, "message": "Failed to create transaction"}

            return {"success": True, "transaction": res[0]}

        except Exception as e:
            logger.error(f"Transaction error: {e}")
            return {"success": False, "message": str(e)}


wallet_service = WalletService()
