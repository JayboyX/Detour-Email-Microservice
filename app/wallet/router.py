"""
Wallet Router
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from decimal import Decimal

from app.wallet.service import wallet_service
from app.wallet.schemas import (
    WalletCreateRequest, DepositRequest, WithdrawalRequest,
    WalletStatus, SuccessResponse
)
from app.shared.database import database_service
from app.kyc.admin_auth import verify_admin_token

router = APIRouter(tags=["wallet"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# User Wallet Endpoints
# ---------------------------------------------------------
@router.get("/user/{user_id}", response_model=SuccessResponse)
async def get_user_wallet(user_id: str):
    wallet = wallet_service.get_wallet_by_user_id(user_id)
    if not wallet:
        return SuccessResponse(success=False, message="Wallet not found", data={"has_wallet": False})

    return SuccessResponse(
        success=True,
        message="Wallet retrieved",
        data={"has_wallet": True, "wallet": wallet}
    )


@router.post("/create", response_model=SuccessResponse)
async def create_wallet(request: WalletCreateRequest):
    user = database_service.get_user_by_id(request.user_id)
    if not user:
        return SuccessResponse(success=False, message="User not found")

    result = wallet_service.create_wallet(request.user_id)
    if result["success"]:
        return SuccessResponse(success=True, message=result["message"], data={"wallet": result.get("wallet")})

    return SuccessResponse(success=False, message=result["message"])


@router.post("/{wallet_id}/deposit", response_model=SuccessResponse)
async def deposit_to_wallet(wallet_id: str, request: DepositRequest):
    result = wallet_service.deposit_funds(wallet_id, float(request.amount), request.description)

    if result["success"]:
        return SuccessResponse(
            success=True,
            message=result["message"],
            data={"new_balance": result["new_balance"], "transaction": result.get("transaction")}
        )

    return SuccessResponse(success=False, message=result["message"])


@router.post("/{wallet_id}/withdraw", response_model=SuccessResponse)
async def withdraw_from_wallet(wallet_id: str, request: WithdrawalRequest):
    result = wallet_service.withdraw_funds(wallet_id, float(request.amount), request.description)

    if result["success"]:
        return SuccessResponse(
            success=True,
            message=result["message"],
            data={"new_balance": result["new_balance"], "transaction": result.get("transaction")}
        )

    return SuccessResponse(success=False, message=result["message"])


@router.get("/{wallet_id}/transactions", response_model=SuccessResponse)
async def get_wallet_transactions(
    wallet_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    transactions = wallet_service.get_transactions(wallet_id, limit, offset)
    wallet = wallet_service.get_wallet_by_id(wallet_id)

    if not wallet:
        return SuccessResponse(success=False, message="Wallet not found")

    return SuccessResponse(
        success=True,
        message="Transactions retrieved",
        data={
            "wallet_id": wallet_id,
            "current_balance": wallet["balance"],
            "total_transactions": len(transactions),
            "transactions": transactions,
        },
    )


@router.get("/{wallet_id}/balance", response_model=SuccessResponse)
async def get_wallet_balance(wallet_id: str):
    wallet = wallet_service.get_wallet_by_id(wallet_id)
    if not wallet:
        return SuccessResponse(success=False, message="Wallet not found")

    return SuccessResponse(
        success=True,
        message="Balance retrieved",
        data={
            "wallet_id": wallet_id,
            "wallet_number": wallet["wallet_number"],
            "balance": wallet["balance"],
            "currency": wallet["currency"],
            "last_updated": wallet["updated_at"],
        },
    )


# ---------------------------------------------------------
# Admin Wallet Endpoints
# ---------------------------------------------------------
@router.get("/admin/all", response_model=SuccessResponse)
async def get_all_wallets(admin_id: str = Depends(verify_admin_token)):
    try:
        endpoint = "/rest/v1/wallets?order=created_at.desc"
        response = database_service.supabase.make_request(
            "GET", endpoint, headers=database_service.supabase.service_headers
        )

        total_balance = sum(float(w.get("balance", 0)) for w in response)

        return SuccessResponse(
            success=True,
            message="All wallets retrieved",
            data={
                "total_wallets": len(response),
                "total_balance": total_balance,
                "wallets": response,
            },
        )
    except Exception as e:
        return SuccessResponse(success=False, message=str(e))


@router.get("/admin/user/{user_id}", response_model=SuccessResponse)
async def admin_get_user_wallet(user_id: str, admin_id: str = Depends(verify_admin_token)):
    wallet = wallet_service.get_wallet_by_user_id(user_id)
    if not wallet:
        return SuccessResponse(success=False, message="Wallet not found for user")

    user = database_service.get_user_by_id(user_id)
    transactions = wallet_service.get_transactions(wallet["id"], limit=10)

    return SuccessResponse(
        success=True,
        message="Wallet details retrieved",
        data={"user": user, "wallet": wallet, "recent_transactions": transactions},
    )


@router.post("/admin/{wallet_id}/adjust", response_model=SuccessResponse)
async def admin_adjust_balance(
    wallet_id: str,
    amount: float,
    description: str = "Admin adjustment",
    admin_id: str = Depends(verify_admin_token),
):
    try:
        wallet = wallet_service.get_wallet_by_id(wallet_id)
        if not wallet:
            return SuccessResponse(success=False, message="Wallet not found")

        if amount >= 0:
            result = wallet_service.deposit_funds(wallet_id, amount, f"Admin deposit: {description}")
        else:
            result = wallet_service.withdraw_funds(wallet_id, abs(amount), f"Admin withdrawal: {description}")

        if result["success"]:
            _log_admin_wallet_action(
                admin_id=admin_id,
                wallet_id=wallet_id,
                amount=amount,
                description=description,
                new_balance=result["new_balance"],
            )
            return SuccessResponse(success=True, message="Balance adjusted", data=result)

        return SuccessResponse(success=False, message=result["message"])

    except Exception as e:
        return SuccessResponse(success=False, message=str(e))


@router.post("/admin/{wallet_id}/status", response_model=SuccessResponse)
async def update_wallet_status(
    wallet_id: str,
    status: WalletStatus,
    admin_id: str = Depends(verify_admin_token),
):
    try:
        updates = {"status": status.value, "updated_at": datetime.utcnow().isoformat()}

        endpoint = f"/rest/v1/wallets?id=eq.{wallet_id}"
        response = database_service.supabase.make_request(
            "PATCH", endpoint, updates, database_service.supabase.service_headers
        )

        if response:
            return SuccessResponse(success=True, message=f"Wallet status updated to {status.value}")

        return SuccessResponse(success=False, message="Failed to update status")

    except Exception as e:
        return SuccessResponse(success=False, message=str(e))


# ---------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------
def _log_admin_wallet_action(admin_id: str, wallet_id: str, amount: float, description: str, new_balance: float):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "admin_id": admin_id,
        "wallet_id": wallet_id,
        "amount": amount,
        "description": description,
        "new_balance": new_balance,
        "action": "balance_adjustment",
    }
    try:
        with open("logs/admin_wallet_actions.log", "a") as f:
            import json
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to log admin wallet action: {e}")
