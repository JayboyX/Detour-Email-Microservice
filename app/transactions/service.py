from decimal import Decimal
from app.shared.database import database_service
from app.wallet.service import wallet_service
from app.transactions.utils import generate_reference, now_iso


class TransactionsService:

    # ------------------------------------------
    # INTERNAL UTILITIES
    # ------------------------------------------
    def _get_wallet(self, user_id):
        wallet = wallet_service.get_wallet_by_user_id(user_id)
        if not wallet:
            return None, {"success": False, "message": "Wallet not found for user"}
        return wallet, None

    def _create_transaction(self, wallet_id, tx_type, amount, description, ref=None, metadata=None, status="completed"):
        data = {
            "wallet_id": wallet_id,
            "transaction_type": tx_type,
            "amount": float(amount),
            "reference": ref or generate_reference(),
            "description": description,
            "status": status,
            "metadata": metadata or {},
            "created_at": now_iso()
        }

        saved = database_service.supabase.make_request(
            "POST",
            "/rest/v1/wallet_transactions",
            data,
            database_service.supabase.service_headers
        )

        return saved[0] if saved else None

    # ------------------------------------------
    # PAYMENT TYPE (wallet deduction)
    # ------------------------------------------
    def process_payment(self, req):

        wallet, error = self._get_wallet(req.user_id)
        if error:
            return error

        # 1. Attempt withdrawal
        withdraw = wallet_service.withdraw_funds(wallet["id"], float(req.amount))
        if not withdraw["success"]:
            return {"success": False, "message": "Insufficient balance"}

        # 2. Log transaction
        tx = self._create_transaction(
            wallet_id=wallet["id"],
            tx_type="payment",
            amount=req.amount,
            description=req.description or f"{req.payment_type} payment",
            ref=req.reference,
            metadata={"payment_type": req.payment_type, **(req.metadata or {})}
        )

        return {
            "success": True,
            "message": "Payment successful",
            "transaction": tx,
            "new_balance": withdraw["new_balance"]
        }

    # ------------------------------------------
    # CREDIT TYPE (wallet top-up: deposits, advance credit)
    # ------------------------------------------
    def process_credit(self, req):

        wallet, error = self._get_wallet(req.user_id)
        if error:
            return error

        # 1. Deposit funds to wallet
        deposit = wallet_service.deposit_funds(wallet["id"], float(req.amount))
        if not deposit["success"]:
            return deposit

        # 2. Log transaction
        tx = self._create_transaction(
            wallet_id=wallet["id"],
            tx_type="deposit",
            amount=req.amount,
            description=req.description or f"{req.credit_type} credit",
            ref=req.reference,
            metadata={"credit_type": req.credit_type, **(req.metadata or {})}
        )

        return {
            "success": True,
            "message": "Credit successful",
            "transaction": tx,
            "new_balance": deposit["new_balance"]
        }

    # ------------------------------------------
    # TRANSFER BETWEEN TWO USERS
    # ------------------------------------------
    def process_transfer(self, req):

        # Get both wallets
        from_wallet, error = self._get_wallet(req.from_user_id)
        if error:
            return error

        to_wallet, error = self._get_wallet(req.to_user_id)
        if error:
            return error

        # 1. Withdraw from sender
        withdraw = wallet_service.withdraw_funds(from_wallet["id"], float(req.amount))
        if not withdraw["success"]:
            return withdraw

        # 2. Deposit to receiver
        deposit = wallet_service.deposit_funds(to_wallet["id"], float(req.amount))
        if not deposit["success"]:
            return deposit

        # 3. Log transactions both sides
        tx_out = self._create_transaction(
            wallet_id=from_wallet["id"],
            tx_type="transfer",
            amount=req.amount,
            description=req.description or "Wallet transfer - debit",
            metadata={"to_user_id": req.to_user_id}
        )

        tx_in = self._create_transaction(
            wallet_id=to_wallet["id"],
            tx_type="transfer",
            amount=req.amount,
            description="Wallet transfer - credit",
            metadata={"from_user_id": req.from_user_id}
        )

        return {
            "success": True,
            "message": "Transfer completed",
            "transactions": {"sender": tx_out, "receiver": tx_in},
            "sender_new_balance": withdraw["new_balance"],
            "receiver_new_balance": deposit["new_balance"]
        }


# Singleton instance
transactions_service = TransactionsService()
