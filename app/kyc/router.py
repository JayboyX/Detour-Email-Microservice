"""
KYC Router
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException

from typing import Optional

from app.kyc.service import kyc_service
from app.kyc.schemas import (
    KYCSubmitRequest,
    KYCListResponse,
    KYCVerifyRequest,
    KYCStatus,
    BAVStatus,
)
from app.auth.schemas import SuccessResponse
from app.kyc.admin_auth import verify_admin_token
from app.shared.database import database_service
from app.wallet.service import wallet_service
from app.email.service import email_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["kyc"])


# ---------------------------------------------------------
# USER KYC SUBMISSION
# ---------------------------------------------------------
@router.post("/submit", response_model=SuccessResponse)
async def submit_kyc(
    user_id: str,
    kyc_data: KYCSubmitRequest,
    background_tasks: BackgroundTasks,
):
    result = kyc_service.submit_kyc(user_id, kyc_data.dict())

    if result["success"]:
        return SuccessResponse(
            success=True,
            message=result["message"],
            data={"kyc_id": result.get("kyc_id")},
        )

    return SuccessResponse(success=False, message=result["message"])


@router.get("/status/{user_id}", response_model=SuccessResponse)
async def get_kyc_status(user_id: str):
    kyc = kyc_service.get_kyc_by_user_id(user_id)

    if not kyc:
        return SuccessResponse(success=False, message="KYC not found")

    return SuccessResponse(success=True, message="KYC status retrieved", data=kyc)


# ---------------------------------------------------------
# ADMIN — LIST KYC
# ---------------------------------------------------------
@router.get("/admin/list", response_model=KYCListResponse)
async def list_all_kyc(
    status: Optional[str] = None,
    admin_id: str = Depends(verify_admin_token),
):
    kycs = kyc_service.get_all_kyc(status)
    stats = kyc_service.get_kyc_stats()

    return KYCListResponse(
        total=stats["total"],
        pending=stats["pending"],
        verified=stats["verified"],
        rejected=stats["rejected"],
        kycs=kycs,
    )


# ---------------------------------------------------------
# ADMIN — GET DETAILS
# ---------------------------------------------------------
@router.get("/admin/details/{kyc_id}", response_model=SuccessResponse)
async def get_kyc_details(
    kyc_id: str,
    admin_id: str = Depends(verify_admin_token),
):
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
        data={"kyc": kyc, "user": user},
    )


# ---------------------------------------------------------
# ADMIN — VERIFY KYC (MANUAL)
# ---------------------------------------------------------
@router.post("/admin/verify", response_model=SuccessResponse)
async def verify_kyc(
    request: KYCVerifyRequest,
    background_tasks: BackgroundTasks,
    admin_id: str = Depends(verify_admin_token),
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

        # Prepare updates
        updates = {
            "kyc_status": request.kyc_status.value,
            "bav_status": request.bav_status.value,
            "admin_notes": request.admin_notes,
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Apply updates
        updated = kyc_service.update_kyc_status(request.kyc_id, updates)
        if not updated:
            return SuccessResponse(success=False, message="Failed to update KYC")

        # VERIFIED FLOW -------------------------------------------------------
        if request.kyc_status == KYCStatus.VERIFIED:
            # Update user
            database_service.supabase.make_request(
                "PATCH",
                f"/rest/v1/users?id=eq.{user_id}",
                {"is_kyc_verified": True, "updated_at": datetime.utcnow().isoformat()},
                database_service.supabase.service_headers,
            )

            # Create wallet
            wallet_result = wallet_service.create_wallet(user_id)

            # Send welcome email
            if wallet_result.get("success"):
                user = database_service.get_user_by_id(user_id)
                wallet_number = wallet_result["wallet"]["wallet_number"]

                background_tasks.add_task(
                    email_service.send_wallet_welcome_email,
                    user["email"],
                    user["full_name"],
                    wallet_number,
                )

            _log_kyc(admin_id, user_id, "verified")

        # REJECTED -------------------------------------------------------------
        elif request.kyc_status == KYCStatus.REJECTED:
            database_service.supabase.make_request(
                "PATCH",
                f"/rest/v1/users?id=eq.{user_id}",
                {"is_kyc_verified": False},
                database_service.supabase.service_headers,
            )

            _log_kyc(admin_id, user_id, "rejected")

        return SuccessResponse(
            success=True,
            message=f"KYC {request.kyc_status.value} successfully",
        )

    except Exception as e:
        logger.error(f"KYC verification error: {e}")
        return SuccessResponse(success=False, message=str(e))


# ---------------------------------------------------------
# CRON — AUTO VERIFY EVERY 2 MINUTES
# ---------------------------------------------------------
# ---------------------------------------------------------
# CRON — AUTO VERIFY EVERY 2 MINUTES (SAFE MODE)
# ---------------------------------------------------------
@router.get("/cron/auto-verify", response_model=SuccessResponse)
async def auto_verify_pending(background_tasks: BackgroundTasks):
    """
    Auto-verify all KYC submissions every 2 minutes.
    Fully automated KYC verification:
        - pending → verified
        - bav_status → verified
        - user.is_kyc_verified → true
        - wallet created if not exists
        - welcome email sent
    """

    try:
        pending_records = database_service.supabase.make_request(
            "GET",
            "/rest/v1/kyc_information?kyc_status=eq.pending",
            database_service.supabase.service_headers,
        )
    except Exception as e:
        logger.error(f"[AUTO-KYC] Failed fetching pending KYC: {e}")
        return SuccessResponse(success=False, message="Failed to read records")

    if not pending_records:
        return SuccessResponse(
            success=True,
            message="No pending KYC to auto-verify",
            data={"verified": 0, "records": []},
        )

    results = []
    verified_count = 0

    for record in pending_records:
        kyc_id = record.get("id")
        user_id = record.get("user_id")

        try:
            if not user_id:
                results.append({"kyc_id": kyc_id, "status": "error", "error": "missing_user_id"})
                continue

            # 1️⃣ Mark KYC verified
            kyc_service.update_kyc_status(
                kyc_id,
                {
                    "kyc_status": "verified",
                    "bav_status": "verified",
                },
            )

            # 2️⃣ Mark user verified
            database_service.supabase.make_request(
                "PATCH",
                f"/rest/v1/users?id=eq.{user_id}",
                {"is_kyc_verified": True},
                database_service.supabase.service_headers,
            )

            # 3️⃣ Create wallet (safe mode — handles duplicates)
            wallet = database_service.get_wallet_by_user_id(user_id)
            if not wallet:
                wallet_result = wallet_service.create_wallet(user_id)
                if wallet_result.get("success"):
                    user = database_service.get_user_by_id(user_id)
                    wallet_number = wallet_result["wallet"]["wallet_number"]
                    background_tasks.add_task(
                        email_service.send_wallet_welcome_email,
                        user["email"],
                        user["full_name"],
                        wallet_number,
                    )

            results.append({"kyc_id": kyc_id, "user_id": user_id, "status": "verified"})
            verified_count += 1

        except Exception as e:
            logger.error(f"[AUTO-KYC] Error verifying KYC {kyc_id}: {e}")
            results.append({"kyc_id": kyc_id, "status": "error", "error": str(e)})
            continue

    return SuccessResponse(
        success=True,
        message="Auto-verification completed",
        data={"verified": verified_count, "records": results},
    )


# ---------------------------------------------------------
# ADMIN — REVOKE KYC (AFTER AUTO-VERIFICATION)
# ---------------------------------------------------------
@router.post("/admin/revoke", response_model=SuccessResponse)
async def revoke_kyc(
    kyc_id: str,
    reason: str,
    background_tasks: BackgroundTasks,
    admin_id: str = Depends(verify_admin_token),
):
    """
    Revoke a user's KYC after verification.
    This will:
      - Set kyc_status = rejected
      - Set bav_status = failed
      - Set is_kyc_verified = false
      - Suspend wallet
      - Send user email notification
    """

    # 1️⃣ Load KYC record
    kyc_record = kyc_service.get_kyc_by_id(kyc_id)
    if not kyc_record:
        return SuccessResponse(success=False, message="KYC record not found")

    user_id = kyc_record["user_id"]

    # 2️⃣ Update KYC status to REJECTED
    updated = kyc_service.update_kyc_status(
        kyc_id,
        {
            "kyc_status": KYCStatus.REJECTED.value,
            "bav_status": BAVStatus.FAILED.value,
            "admin_notes": reason,
        },
    )

    if not updated:
        return SuccessResponse(success=False, message="Failed to update KYC record")

    # 3️⃣ Update user → remove verification
    database_service.supabase.make_request(
        "PATCH",
        f"/rest/v1/users?id=eq.{user_id}",
        {
            "is_kyc_verified": False,
            "updated_at": datetime.utcnow().isoformat(),
        },
        database_service.supabase.service_headers,
    )

    # 4️⃣ Suspend wallet
    wallet_data = database_service.supabase.make_request(
        "GET",
        f"/rest/v1/wallets?user_id=eq.{user_id}",
        database_service.supabase.service_headers,
    )

    if wallet_data:
        wallet_id = wallet_data[0]["id"]

        database_service.supabase.make_request(
            "PATCH",
            f"/rest/v1/wallets?id=eq.{wallet_id}",
            {"status": "suspended"},
            database_service.supabase.service_headers,
        )

    # 5️⃣ Send revocation email
    user = database_service.get_user_by_id(user_id)

    if user:
        background_tasks.add_task(
            email_service.send_kyc_revoked_email,
            user["email"],
            user["full_name"],
            reason,
        )

    # 6️⃣ Log the action
    _log_kyc(admin_id, user_id, f"KYC revoked — Reason: {reason}")

    return SuccessResponse(
        success=True,
        message="KYC revoked successfully",
        data={"user_id": user_id, "reason": reason},
    )



# ---------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------
def _log_kyc(admin_id: Optional[str], user_id: str, status: str):
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
