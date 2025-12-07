# app/transactions/router.py

from fastapi import APIRouter, HTTPException
from app.transactions.schemas import PaymentRequest, CreditRequest, TransferRequest
from app.transactions.service import transactions_service
from app.auth.schemas import SuccessResponse
from app.subscriptions.service import subscription_service
from app.wallet.service import wallet_service
from decimal import Decimal

router = APIRouter(tags=["transactions"])


# -------------------------------------
# PAYMENT (DEDUCT FROM WALLET)
# -------------------------------------
@router.post("/pay", response_model=SuccessResponse)
async def make_payment(req: PaymentRequest):
    result = transactions_service.process_payment(req)
    return SuccessResponse(**result)


# -------------------------------------
# CREDIT (ADD FUNDS / ADVANCE)
# -------------------------------------
@router.post("/credit", response_model=SuccessResponse)
async def credit_wallet(req: CreditRequest):

    user_id = req.user_id
    amount = Decimal(req.amount)

    # 1️⃣ Validate amount
    if amount <= 0:
        raise HTTPException(400, "Amount must be greater than zero")

    # 2️⃣ Fetch wallet
    wallet = wallet_service.get_wallet_by_user_id(user_id)
    if not wallet:
        raise HTTPException(404, "Wallet not found")

    balance = Decimal(wallet["balance"])

    # 3️⃣ Fetch subscription limits (weekly cap + percentage calc)
    sub_limits = subscription_service.get_user_limits(user_id)
    if not sub_limits or not sub_limits["package"]:
        raise HTTPException(403, "You must have an active subscription")

    package = sub_limits["package"]
    weekly_cap = Decimal(package["weekly_advance_limit"])
    percentage_limit = Decimal(sub_limits["percentage_limit"])
    available_limit = Decimal(sub_limits["available"])

    # 4️⃣ Outstanding advances logic
    outstanding = subscription_service.get_outstanding_advances(user_id)
    if outstanding > 0:
        raise HTTPException(
            403,
            f"You have an unpaid advance of R{outstanding}. Please settle before requesting more."
        )

    # 5️⃣ Final limit enforcement
    if amount > available_limit:
        raise HTTPException(
            403,
            f"Your available advance is R{available_limit}. "
            f"You requested R{amount}."
        )

    # 6️⃣ Process the credit transaction
    result = transactions_service.process_credit(req)

    return SuccessResponse(**result)


# -------------------------------------
# TRANSFER FUNDS
# -------------------------------------
@router.post("/transfer", response_model=SuccessResponse)
async def transfer(req: TransferRequest):
    result = transactions_service.process_transfer(req)
    return SuccessResponse(**result)
