from decimal import Decimal
from app.shared.database import database_service
from app.wallet.service import wallet_service
from app.transactions.utils import generate_reference, now_iso


class TransactionsService:

    # -----------------------------
    def _get_wallet(self, user_id):
        wallet = wallet_service.get_wallet_by_user_id(user_id)
        if not wallet:
            return None, {"success": False, "message": "Wallet not found for user"}
        return wallet, None

    def _log(self, wallet_id, tx_type, amount, description, ref=None, metadata=None):
        return wallet_service.create_transaction(
            wallet_id=wallet_id,
            transaction_type=tx_type,
            amount=float(amount),
            description=description,
            reference=ref or generate_reference(),
            metadata=metadata or {}
        )

    # -----------------------------
    # PAYMENT = DEBIT
    # -----------------------------
    def process_payment(self, req):
        wallet, error = self._get_wallet(req.user_id)
        if error:
            return error

        debit_amount = -abs(float(req.amount))  # negative for debit

        result = wallet_service.update_wallet_balance(wallet["id"], debit_amount, "payment")
        if not result["success"]:
            return result

        tx = self._log(
            wallet["id"],
            "payment",
            req.amount,
            req.description or f"{req.payment_type} payment",
            metadata=req.metadata
        )

        return {
            "success": True,
            "message": "Payment successful",
            "transaction": tx,
            "new_balance": result["new_balance"]
        }

    # -----------------------------
    # CREDIT = DEPOSIT
    # -----------------------------
    def process_credit(self, req):
        wallet, error = self._get_wallet(req.user_id)
        if error:
            return error

        credit_amount = abs(float(req.amount))

        result = wallet_service.update_wallet_balance(wallet["id"], credit_amount, "deposit")
        if not result["success"]:
            return result

        tx = self._log(
            wallet["id"],
            "deposit",
            req.amount,
            req.description or f"{req.credit_type} credit",
            metadata=req.metadata
        )

        return {
            "success": True,
            "message": "Credit successful",
            "transaction": tx,
            "new_balance": result["new_balance"]
        }

    # -----------------------------
    # TRANSFER = DEBIT THEN CREDIT
    # -----------------------------
    def process_transfer(self, req):
        from_wallet, error = self._get_wallet(req.from_user_id)
        if error:
            return error

        to_wallet, error = self._get_wallet(req.to_user_id)
        if error:
            return error

        amt = float(req.amount)

        # debit sender
        debit = wallet_service.update_wallet_balance(from_wallet["id"], -amt, "transfer")
        if not debit["success"]:
            return debit

        # credit receiver
        credit = wallet_service.update_wallet_balance(to_wallet["id"], amt, "transfer")
        if not credit["success"]:
            return credit

        # log sender
        self._log(
            from_wallet["id"],
            "transfer",
            amt,
            "Wallet transfer - debit",
            metadata={"to_user_id": req.to_user_id}
        )

        # log receiver
        self._log(
            to_wallet["id"],
            "transfer",
            amt,
            "Wallet transfer - credit",
            metadata={"from_user_id": req.from_user_id}
        )

        return {
            "success": True,
            "message": "Transfer completed",
            "sender_new_balance": debit["new_balance"],
            "receiver_new_balance": credit["new_balance"]
        }


transactions_service = TransactionsService()
