"""
Wallet microservice router
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from decimal import Decimal
from app.wallet.service import wallet_service
from app.wallet.schemas import *
from app.shared.auth import auth_service
from app.shared.database import database_service
from app.kyc.admin_auth import verify_admin_token  # Reuse admin auth

router = APIRouter(tags=["wallet"])

# ========== User Wallet Endpoints ==========

@router.get("/user/{user_id}", response_model=SuccessResponse)
async def get_user_wallet(user_id: str):
    """Get wallet details for user"""
    wallet = wallet_service.get_wallet_by_user_id(user_id)
    if not wallet:
        return SuccessResponse(
            success=False, 
            message="Wallet not found",
            data={"has_wallet": False}
        )
    
    return SuccessResponse(
        success=True,
        message="Wallet retrieved",
        data={
            "has_wallet": True,
            "wallet": wallet
        }
    )

@router.post("/create", response_model=SuccessResponse)
async def create_wallet(request: WalletCreateRequest):
    """Create a new wallet for user"""
    # Check if user exists
    user = database_service.get_user_by_id(request.user_id)
    if not user:
        return SuccessResponse(success=False, message="User not found")
    
    # Create wallet
    result = wallet_service.create_wallet(request.user_id)
    
    if result["success"]:
        return SuccessResponse(
            success=True,
            message=result["message"],
            data={"wallet": result.get("wallet")}
        )
    else:
        return SuccessResponse(success=False, message=result["message"])

@router.post("/{wallet_id}/deposit", response_model=SuccessResponse)
async def deposit_to_wallet(
    wallet_id: str,
    request: DepositRequest
):
    """Deposit funds to wallet"""
    result = wallet_service.deposit_funds(
        wallet_id=wallet_id,
        amount=float(request.amount),
        description=request.description
    )
    
    if result["success"]:
        return SuccessResponse(
            success=True,
            message=result["message"],
            data={
                "new_balance": result["new_balance"],
                "transaction": result.get("transaction")
            }
        )
    else:
        return SuccessResponse(success=False, message=result["message"])

@router.post("/{wallet_id}/withdraw", response_model=SuccessResponse)
async def withdraw_from_wallet(
    wallet_id: str,
    request: WithdrawalRequest
):
    """Withdraw funds from wallet"""
    result = wallet_service.withdraw_funds(
        wallet_id=wallet_id,
        amount=float(request.amount),
        description=request.description
    )
    
    if result["success"]:
        return SuccessResponse(
            success=True,
            message=result["message"],
            data={
                "new_balance": result["new_balance"],
                "transaction": result.get("transaction")
            }
        )
    else:
        return SuccessResponse(success=False, message=result["message"])

@router.get("/{wallet_id}/transactions", response_model=SuccessResponse)
async def get_wallet_transactions(
    wallet_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get wallet transaction history"""
    transactions = wallet_service.get_transactions(wallet_id, limit, offset)
    wallet = wallet_service.get_wallet_by_id(wallet_id)
    
    if not wallet:
        return SuccessResponse(success=False, message="Wallet not found")
    
    return SuccessResponse(
        success=True,
        message="Transactions retrieved",
        data={
            "wallet_id": wallet_id,
            "current_balance": wallet['balance'],
            "total_transactions": len(transactions),
            "transactions": transactions
        }
    )

@router.get("/{wallet_id}/balance", response_model=SuccessResponse)
async def get_wallet_balance(wallet_id: str):
    """Get wallet balance"""
    wallet = wallet_service.get_wallet_by_id(wallet_id)
    if not wallet:
        return SuccessResponse(success=False, message="Wallet not found")
    
    return SuccessResponse(
        success=True,
        message="Balance retrieved",
        data={
            "wallet_id": wallet_id,
            "wallet_number": wallet['wallet_number'],
            "balance": wallet['balance'],
            "currency": wallet['currency'],
            "last_updated": wallet['updated_at']
        }
    )

# ========== Admin Wallet Endpoints ==========

@router.get("/admin/all", response_model=SuccessResponse)
async def get_all_wallets(
    admin_id: str = Depends(verify_admin_token)
):
    """Get all wallets (admin only)"""
    try:
        endpoint = "/rest/v1/wallets?order=created_at.desc"
        response = database_service.supabase.make_request(
            "GET", endpoint, headers=database_service.supabase.service_headers
        )
        
        total_balance = sum(float(w['balance']) for w in response if w.get('balance'))
        
        return SuccessResponse(
            success=True,
            message="All wallets retrieved",
            data={
                "total_wallets": len(response),
                "total_balance": total_balance,
                "wallets": response
            }
        )
    except Exception as e:
        return SuccessResponse(success=False, message=str(e))

@router.get("/admin/user/{user_id}", response_model=SuccessResponse)
async def admin_get_user_wallet(
    user_id: str,
    admin_id: str = Depends(verify_admin_token)
):
    """Get user wallet details (admin only)"""
    wallet = wallet_service.get_wallet_by_user_id(user_id)
    if not wallet:
        return SuccessResponse(
            success=False, 
            message="Wallet not found for user"
        )
    
    # Get user details
    user = database_service.get_user_by_id(user_id)
    
    # Get transaction history
    transactions = wallet_service.get_transactions(wallet['id'], limit=10)
    
    return SuccessResponse(
        success=True,
        message="Wallet details retrieved",
        data={
            "user": user,
            "wallet": wallet,
            "recent_transactions": transactions
        }
    )

@router.post("/admin/{wallet_id}/adjust", response_model=SuccessResponse)
async def admin_adjust_balance(
    wallet_id: str,
    amount: float,
    description: str = "Admin adjustment",
    admin_id: str = Depends(verify_admin_token)
):
    """Admin adjustment of wallet balance"""
    try:
        wallet = wallet_service.get_wallet_by_id(wallet_id)
        if not wallet:
            return SuccessResponse(success=False, message="Wallet not found")
        
        # Update balance
        if amount >= 0:
            result = wallet_service.deposit_funds(wallet_id, amount, f"Admin deposit: {description}")
        else:
            result = wallet_service.withdraw_funds(wallet_id, abs(amount), f"Admin withdrawal: {description}")
        
        if result["success"]:
            # Log admin action
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "admin_id": admin_id,
                "wallet_id": wallet_id,
                "action": "balance_adjustment",
                "amount": amount,
                "description": description,
                "new_balance": result["new_balance"]
            }
            
            try:
                with open('logs/admin_wallet_actions.log', 'a') as f:
                    import json
                    f.write(json.dumps(log_entry) + '\n')
            except Exception as e:
                logger.error(f"Failed to log admin action: {e}")
            
            return SuccessResponse(
                success=True,
                message="Balance adjusted",
                data=result
            )
        else:
            return SuccessResponse(success=False, message=result["message"])
            
    except Exception as e:
        return SuccessResponse(success=False, message=str(e))

@router.post("/admin/{wallet_id}/status", response_model=SuccessResponse)
async def update_wallet_status(
    wallet_id: str,
    status: WalletStatus,
    admin_id: str = Depends(verify_admin_token)
):
    """Update wallet status (admin only)"""
    try:
        updates = {
            'status': status.value,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        endpoint = f"/rest/v1/wallets?id=eq.{wallet_id}"
        response = database_service.supabase.make_request(
            "PATCH", endpoint, updates, database_service.supabase.service_headers
        )
        
        if response:
            return SuccessResponse(
                success=True,
                message=f"Wallet status updated to {status.value}"
            )
        else:
            return SuccessResponse(success=False, message="Failed to update status")
            
    except Exception as e:
        return SuccessResponse(success=False, message=str(e))