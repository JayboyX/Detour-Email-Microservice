"""
KYC Router
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, BackgroundTasks
from typing import Optional

from app.kyc.service import kyc_service
from app.kyc.schemas import (
    KYCSubmitRequest, KYCListResponse, KYCVerifyRequest, KYCStatus
)
from app.auth.schemas import SuccessResponse
from app.kyc.admin_auth import verify_admin_token
from app.shared.database import database_service
from app.wallet.service import wallet_service
from app.email.service import email_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["kyc"])


# ---------------------------------------------------------
# User KYC Endpoints
# ---------------------------------------------------------
@router.post("/submit", response_model=SuccessResponse)
async def submit_kyc(user_id: str, kyc_data: KYCSubmitRequest, background_tasks: BackgroundTasks):
    result = kyc_service.submit_kyc(user_id, kyc_data.dict())

    if result["success"]:
        return SuccessResponse(
            success=True,
            message=result["message"],
            data={"kyc_id": result.get("kyc_id")}
        )

    return SuccessResponse(success=False, message=result["message"])


@router.get("/status/{user_id}", response_model=SuccessResponse)
async def get_kyc_status(user_id: str):
    kyc = kyc_service.get_kyc_by_user_id(user_id)

    if not kyc:
        return SuccessResponse(success=False, message="KYC not found")

    return SuccessResponse(success=True, message="KYC status retrieved", data=kyc)


# ---------------------------------------------------------
# Admin KYC Endpoints
# ---------------------------------------------------------
@router.get("/admin/list", response_model=KYCListResponse)
async def list_all_kyc(
    status: Optional[str] = None,
    admin_id: str = Depends(verify_admin_token)
):
    kycs = kyc_service.get_all_kyc(status)
    stats = kyc_service.get_kyc_stats()

    return KYCListResponse(
        total=stats["total"],
        pending=stats["pending"],
        verified=stats["verified"],
        rejected=stats["rejected"],
        kycs=kycs
    )


@router.get("/admin/details/{kyc_id}", response_model=SuccessResponse)
async def get_kyc_details(
    kyc_id: str,
    admin_id: str = Depends(verify_admin_token)
):
    try:
        endpoint = f"/rest/v1/kyc_information?id=eq.{kyc_id}"
        response = database_service.supabase.make_request(
            "GET", endpoint, headers=database_service.supabase.service_headers
        )

        if not response:
            return SuccessResponse(success=False, message="KYC not found")

        kyc = response[0]
        user = database_service.get_user_by_id(kyc["user_id"])

        return SuccessResponse(
            success=True,
            message="KYC details retrieved",
            data={"kyc": kyc, "user": user}
        )

    except Exception as e:
        return SuccessResponse(success=False, message=str(e))


@router.post("/admin/verify", response_model=SuccessResponse)
async def verify_kyc(
    request: KYCVerifyRequest,
    background_tasks: BackgroundTasks,
    admin_id: str = Depends(verify_admin_token)
):
    try:
        # Load KYC record
        endpoint = f"/rest/v1/kyc_information?id=eq.{request.kyc_id}"
        kyc_response = database_service.supabase.make_request(
            "GET", endpoint, headers=database_service.supabase.service_headers
        )

        if not kyc_response:
            return SuccessResponse(success=False, message="KYC not found")

        kyc_record = kyc_response[0]
        user_id = kyc_record["user_id"]

        # Update status
        updates = {
            "kyc_status": request.kyc_status.value,
            "bav_status": request.bav_status.value,
            "admin_notes": request.admin_notes,
            "updated_at": datetime.utcnow().isoformat(),
        }

        if not kyc_service.update_kyc_status(request.kyc_id, updates):
            return SuccessResponse(success=False, message="Failed to update KYC")

        # Verified flow
        if request.kyc_status == KYCStatus.VERIFIED:

            # Mark user verified
            user_updates = {"is_kyc_verified": True}
            user_endpoint = f"/rest/v1/users?id=eq.{user_id}"
            database_service.supabase.make_request(
                "PATCH", user_endpoint, user_updates, database_service.supabase.service_headers
            )

            # Create wallet
            wallet_result = wallet_service.create_wallet(user_id)

            # Send welcome email
            if wallet_result.get("success"):
                user = database_service.get_user_by_id(user_id)
                wallet_number = wallet_result.get("wallet", {}).get("wallet_number")

                background_tasks.add_task(
                    email_service.send_wallet_welcome_email,
                    user["email"],
                    user["full_name"],
                    wallet_number
                )

            _log_kyc(admin_id, user_id, request.kyc_status.value)

        # Rejected flow
        elif request.kyc_status == KYCStatus.REJECTED:
            user_updates = {
                "is_kyc_verified": False,
                "updated_at": datetime.utcnow().isoformat()
            }
            user_endpoint = f"/rest/v1/users?id=eq.{user_id}"
            database_service.supabase.make_request(
                "PATCH", user_endpoint, user_updates, database_service.supabase.service_headers
            )

            _log_kyc(admin_id, user_id, request.kyc_status.value)

        return SuccessResponse(
            success=True,
            message=f"KYC {request.kyc_status.value} successfully"
        )

    except Exception as e:
        logger.error(f"KYC verification error: {e}")
        return SuccessResponse(success=False, message=str(e))


# ---------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------
def _log_kyc(admin_id: str, user_id: str, status: str):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "admin_id": admin_id,
        "user_id": user_id,
        "action": f"KYC {status}",
    }
    try:
        with open("logs/kyc_audit.log", "a") as f:
            import json
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to write KYC audit log: {e}")
