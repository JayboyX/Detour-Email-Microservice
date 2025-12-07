"""
Authentication Router
"""

from fastapi import APIRouter, Depends, BackgroundTasks, status
from typing import Dict, Any
from datetime import datetime, timedelta, timezone
import logging
import httpx

from app.auth.schemas import (
    UserCreateRequest, UserLoginRequest, VerifyEmailRequest,
    ResendVerificationRequest, SuccessResponse,
    SendOTPRequest, VerifyOTPRequest, ResendOTPRequest
)
from app.auth.service import auth_service
from app.email.service import email_service
from app.sms.service import sms_service
from app.sms.otp_service import otp_service
from app.shared.database import database_service
from app.shared.auth import auth_service as shared_auth_service
from app.config import settings
from app.kyc.admin_auth import verify_admin_token

logger = logging.getLogger(__name__)
router = APIRouter(tags=["authentication"])


# ---------------------------------------------------------
# Email Verification
# ---------------------------------------------------------
@router.post("/signup", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreateRequest, background_tasks: BackgroundTasks):
    try:
        print("🔥 SIGNUP PAYLOAD RECEIVED:", user_data.dict())
        result = auth_service.register_user(user_data.dict())
        if not result["success"]:
            return SuccessResponse(success=False, message=result["message"])

        user = result["user"]
        verification_token = shared_auth_service.create_verification_token(user["id"], user["email"])
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.verification_token_expire_hours)

        database_service.set_verification_token(user["id"], verification_token, expires_at)
        verification_url = f"{settings.api_base_url}/verify-email?token={verification_token}"

        background_tasks.add_task(
            email_service.send_verification_email,
            user["email"],
            verification_url,
            user["full_name"]
        )

        return SuccessResponse(
            success=True,
            message="Account created! Please check your email for verification.",
            data={
                "user_id": user["id"],
                "email": user["email"],
                "requires_verification": True
            }
        )

    except Exception as e:
        return SuccessResponse(success=False, message=f"Registration failed: {str(e)}")


@router.post("/verify-email", response_model=SuccessResponse)
async def verify_email(request: VerifyEmailRequest):
    result = auth_service.verify_email_token(request.token)

    if result["success"]:
        return SuccessResponse(
            success=True,
            message="Email verified successfully!" if not result.get("already_verified") else "Email already verified",
            data={
                "user_id": result["user"]["id"],
                "email": result["user"]["email"],
                "verified": result.get("verified", False),
                "already_verified": result.get("already_verified", False)
            }
        )

    return SuccessResponse(success=False, message=result["message"])


@router.post("/resend-verification", response_model=SuccessResponse)
async def resend_verification(request: ResendVerificationRequest, background_tasks: BackgroundTasks):
    try:
        user = database_service.get_user_by_email(request.email)
        if not user:
            return SuccessResponse(success=False, message="User not found")

        if user.get("email_verified"):
            return SuccessResponse(success=False, message="Email already verified")

        token = shared_auth_service.create_verification_token(user["id"], user["email"])
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.verification_token_expire_hours)
        database_service.set_verification_token(user["id"], token, expires_at)

        verification_url = f"{settings.api_base_url}/verify-email?token={token}"

        background_tasks.add_task(
            email_service.send_verification_email,
            user["email"],
            verification_url,
            user["full_name"]
        )

        return SuccessResponse(success=True, message="Verification email resent successfully")

    except Exception as e:
        return SuccessResponse(success=False, message=f"Failed to resend: {str(e)}")


# ---------------------------------------------------------
# Login & Status
# ---------------------------------------------------------
@router.post("/login", response_model=SuccessResponse)
async def login(login_data: UserLoginRequest):
    result = auth_service.login_user(login_data.email, login_data.password)

    if result["success"]:
        return SuccessResponse(
            success=True,
            message="Login successful",
            data={
                "access_token": result["access_token"],
                "token_type": "bearer",
                "user": {
                    "id": result["user"]["id"],
                    "email": result["user"]["email"],
                    "full_name": result["user"]["full_name"],
                    "email_verified": result["user"]["email_verified"]
                }
            }
        )

    if result.get("requires_verification"):
        return SuccessResponse(
            success=False,
            message=result["message"],
            data={"requires_verification": True}
        )

    return SuccessResponse(success=False, message=result["message"])


@router.get("/check-verification/{email}", response_model=SuccessResponse)
async def check_verification(email: str):
    try:
        user = database_service.get_user_by_email(email)
        if not user:
            return SuccessResponse(success=False, message="User not found")

        return SuccessResponse(
            success=True,
            message="Verification status retrieved",
            data={
                "email_verified": user.get("email_verified", False),
                "email": user["email"],
                "user_id": user["id"]
            }
        )

    except Exception as e:
        return SuccessResponse(success=False, message=f"Check failed: {str(e)}")


# ---------------------------------------------------------
# SMS OTP Helpers (Phone Verification)
# ---------------------------------------------------------
def get_kyc_by_user_id(user_id: str):
    try:
        endpoint = f"/rest/v1/kyc_information?user_id=eq.{user_id}"
        response = database_service.supabase.make_request(
            "GET", endpoint, headers=database_service.supabase.anon_headers
        )
        return response[0] if response else None
    except Exception as e:
        logger.error(f"Error getting KYC: {e}")
        return None


def set_phone_otp(user_id: str, otp_code: str, expires_at: datetime) -> bool:
    try:
        updates = {
            "phone_verification_otp": otp_code,
            "phone_otp_expires_at": expires_at.isoformat(),
            "phone_otp_last_sent": datetime.now(timezone.utc).isoformat(),
            "phone_otp_attempts": 0,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        kyc_info = get_kyc_by_user_id(user_id)

        if kyc_info:
            endpoint = f"/rest/v1/kyc_information?user_id=eq.{user_id}"
        else:
            updates["user_id"] = user_id
            updates.update({
                "id_number": "pending",
                "first_name": "pending",
                "last_name": "pending",
                "date_of_birth": "2000-01-01",
                "phone_number": "pending",
                "address": "pending",
                "bank_account_number": "pending",
                "bank_name": "pending"
            })
            endpoint = "/rest/v1/kyc_information"

        response = database_service.supabase.make_request(
            "PATCH" if kyc_info else "POST",
            endpoint,
            updates,
            database_service.supabase.service_headers
        )
        return bool(response)

    except Exception as e:
        logger.error(f"Error setting phone OTP: {e}")
        return False


def verify_phone_otp_db(user_id: str, otp_code: str) -> Dict[str, Any]:
    try:
        kyc = get_kyc_by_user_id(user_id)
        if not kyc:
            return {"success": False, "error": "KYC information not found"}

        if kyc.get("phone_verified"):
            return {"success": True, "already_verified": True}

        attempts = kyc.get("phone_otp_attempts", 0)
        if attempts >= settings.otp_max_attempts:
            return {"success": False, "error": "Too many attempts"}

        stored = kyc.get("phone_verification_otp")
        expiry = kyc.get("phone_otp_expires_at")

        if not stored or not expiry:
            return {"success": False, "error": "No OTP found"}

        if otp_service.is_otp_valid(stored, expiry, otp_code):
            updates = {
                "phone_verified": True,
                "phone_verification_otp": None,
                "phone_otp_expires_at": None,
                "phone_otp_attempts": 0,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            endpoint = f"/rest/v1/kyc_information?user_id=eq.{user_id}"
            database_service.supabase.make_request("PATCH", endpoint, updates, database_service.supabase.service_headers)

            return {"success": True, "verified": True, "user_id": user_id}

        updates = {
            "phone_otp_attempts": attempts + 1,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        endpoint = f"/rest/v1/kyc_information?user_id=eq.{user_id}"
        database_service.supabase.make_request("PATCH", endpoint, updates, database_service.supabase.service_headers)

        remaining = settings.otp_max_attempts - (attempts + 1)
        return {
            "success": False,
            "error": "Invalid OTP",
            "remaining_attempts": remaining,
            "user_id": user_id
        }

    except Exception as e:
        logger.error(f"Error verifying OTP: {e}")
        return {"success": False, "error": f"Verification failed: {str(e)}", "user_id": user_id}


def can_resend_otp(last_sent) -> bool:
    try:
        if not last_sent:
            return True

        if isinstance(last_sent, str):
            last_sent = datetime.fromisoformat(last_sent.replace("Z", "+00:00"))

        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)

        return (datetime.now(timezone.utc) - last_sent).total_seconds() >= settings.otp_resend_delay_seconds

    except Exception as e:
        logger.error(f"Error checking resend eligibility: {e}")
        return True


# ---------------------------------------------------------
# Phone OTP API
# ---------------------------------------------------------
@router.post("/send-phone-otp", response_model=SuccessResponse)
async def send_phone_otp(request: SendOTPRequest, background_tasks: BackgroundTasks):
    try:
        user = database_service.get_user_by_id(request.user_id)
        if not user:
            return SuccessResponse(success=False, message="User not found")

        kyc = get_kyc_by_user_id(request.user_id)

        if kyc and kyc.get("phone_verified"):
            return SuccessResponse(
                success=True,
                message="Phone already verified",
                data={"already_verified": True, "user_id": request.user_id}
            )

        last_sent = kyc.get("phone_otp_last_sent") if kyc else None
        if last_sent and not can_resend_otp(last_sent):
            return SuccessResponse(success=False, message="Please wait 60 seconds")

        otp_code = otp_service.generate_otp()
        expires_at = otp_service.get_otp_expiry()

        if not set_phone_otp(request.user_id, otp_code, expires_at):
            return SuccessResponse(success=False, message="Failed to generate OTP")

        background_tasks.add_task(
            sms_service.send_otp_sms,
            request.phone_number,
            otp_code,
            user.get("full_name", "User")
        )

        return SuccessResponse(
            success=True,
            message=f"OTP sent to {request.phone_number}",
            data={
                "expires_in_minutes": settings.otp_expiry_minutes,
                "user_id": request.user_id,
                "phone_number": request.phone_number
            }
        )

    except Exception as e:
        return SuccessResponse(
            success=False,
            message=f"Failed to send OTP: {str(e)}",
            data={"user_id": request.user_id}
        )


@router.post("/verify-phone-otp", response_model=SuccessResponse)
async def verify_phone_otp(request: VerifyOTPRequest):
    result = verify_phone_otp_db(request.user_id, request.otp_code)

    if result.get("success"):
        return SuccessResponse(
            success=True,
            message="Phone number verified successfully!",
            data={
                "verified": result.get("verified", True),
                "already_verified": result.get("already_verified", False),
                "user_id": request.user_id
            }
        )

    return SuccessResponse(
        success=False,
        message=result.get("error", "Verification failed"),
        data={
            "remaining_attempts": result.get("remaining_attempts"),
            "user_id": request.user_id
        }
    )


@router.post("/resend-phone-otp", response_model=SuccessResponse)
async def resend_phone_otp(request: ResendOTPRequest, background_tasks: BackgroundTasks):
    try:
        user = database_service.get_user_by_id(request.user_id)
        if not user:
            return SuccessResponse(success=False, message="User not found")

        kyc = get_kyc_by_user_id(request.user_id)
        if not kyc:
            return SuccessResponse(success=False, message="KYC information not found")

        if kyc.get("phone_verified"):
            return SuccessResponse(
                success=True,
                message="Phone already verified",
                data={"already_verified": True}
            )

        last_sent = kyc.get("phone_otp_last_sent")
        if last_sent and not can_resend_otp(last_sent):
            return SuccessResponse(success=False, message="Please wait 60 seconds")

        otp_code = otp_service.generate_otp()
        expires_at = otp_service.get_otp_expiry()

        if not set_phone_otp(request.user_id, otp_code, expires_at):
            return SuccessResponse(success=False, message="Failed to generate OTP")

        phone = kyc.get("phone_number") or user.get("phone_number")
        if not phone:
            return SuccessResponse(success=False, message="Phone number not found")

        background_tasks.add_task(
            sms_service.send_otp_sms,
            phone,
            otp_code,
            user.get("full_name", "User")
        )

        return SuccessResponse(
            success=True,
            message="OTP resent successfully",
            data={"expires_in_minutes": settings.otp_expiry_minutes}
        )

    except Exception as e:
        return SuccessResponse(
            success=False,
            message=f"Failed to resend OTP: {str(e)}",
            data={"user_id": request.user_id}
        )


# ---------------------------------------------------------
# SMS Test & Admin Registration
# ---------------------------------------------------------
@router.get("/test-sms-connection", response_model=SuccessResponse)
async def test_sms_connection():
    try:
        result = sms_service.test_connection()

        if result.get("success"):
            return SuccessResponse(
                success=True,
                message="SMS service is connected",
                data=result
            )

        return SuccessResponse(
            success=False,
            message=f"SMS service test failed: {result.get('error')}",
            data=result
        )

    except Exception as e:
        return SuccessResponse(success=False, message=f"SMS test failed: {str(e)}")


@router.post("/admin/register", response_model=SuccessResponse)
async def register_admin(
    user_id: str,
    admin_user_id: str = Depends(verify_admin_token)
):
    try:
        admin_data = {
            "user_id": user_id,
            "role": "moderator",
            "permissions": ["read", "write", "verify"]
        }

        endpoint = "/rest/v1/admins"
        response = database_service.supabase.make_request(
            "POST", endpoint, admin_data, database_service.supabase.service_headers
        )

        return SuccessResponse(
            success=True,
            message="Admin registered successfully",
            data={"admin_id": response[0]["id"] if response else None}
        )

    except Exception as e:
        return SuccessResponse(success=False, message=str(e))
