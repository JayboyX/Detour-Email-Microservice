"""
Main authentication router
Combines email, SMS, and user authentication
"""
from fastapi import APIRouter, Depends, BackgroundTasks, status
from typing import Dict, Any
from datetime import datetime, timedelta, timezone
import logging

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

logger = logging.getLogger(__name__)
router = APIRouter(tags=["authentication"])

# ========== Email Verification Endpoints ==========
@router.post("/signup", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    user_data: UserCreateRequest,
    background_tasks: BackgroundTasks
):
    """Register a new user and send verification email"""
    try:
        # Register user
        result = auth_service.register_user(user_data.dict())
        if not result["success"]:
            return SuccessResponse(success=False, message=result["message"])
        
        user = result["user"]
        
        # Generate verification token
        verification_token = shared_auth_service.create_verification_token(user['id'], user['email'])
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.verification_token_expire_hours)
        
        # Save token
        database_service.set_verification_token(user['id'], verification_token, expires_at)
        
        # Create verification URL
        verification_url = f"{settings.api_base_url}/verify-email?token={verification_token}"
        
        # Send email in background
        background_tasks.add_task(
            email_service.send_verification_email,
            user['email'],
            verification_url,
            user['full_name']
        )
        
        return SuccessResponse(
            success=True,
            message="Account created! Please check your email for verification.",
            data={
                "user_id": user['id'],
                "email": user['email'],
                "requires_verification": True
            }
        )
        
    except Exception as e:
        return SuccessResponse(success=False, message=f"Registration failed: {str(e)}")

@router.post("/verify-email", response_model=SuccessResponse)
async def verify_email(request: VerifyEmailRequest):
    """Verify email using JWT token"""
    result = auth_service.verify_email_token(request.token)
    
    if result["success"]:
        if result.get("already_verified"):
            message = "Email already verified"
        else:
            message = "Email verified successfully!"
        
        return SuccessResponse(
            success=True,
            message=message,
            data={
                "user_id": result["user"]["id"],
                "email": result["user"]["email"],
                "verified": result.get("verified", False),
                "already_verified": result.get("already_verified", False)
            }
        )
    else:
        return SuccessResponse(success=False, message=result["message"])

@router.post("/resend-verification", response_model=SuccessResponse)
async def resend_verification(
    request: ResendVerificationRequest,
    background_tasks: BackgroundTasks
):
    """Resend verification email"""
    try:
        user = database_service.get_user_by_email(request.email)
        if not user:
            return SuccessResponse(success=False, message="User not found")
        
        if user.get('email_verified'):
            return SuccessResponse(success=False, message="Email already verified")
        
        # Generate new token
        verification_token = shared_auth_service.create_verification_token(user['id'], user['email'])
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.verification_token_expire_hours)
        
        # Save new token
        database_service.set_verification_token(user['id'], verification_token, expires_at)
        
        # Create verification URL
        verification_url = f"{settings.api_base_url}/verify-email?token={verification_token}"
        
        # Resend email in background
        background_tasks.add_task(
            email_service.send_verification_email,
            user['email'],
            verification_url,
            user['full_name']
        )
        
        return SuccessResponse(
            success=True,
            message="Verification email resent successfully"
        )
        
    except Exception as e:
        return SuccessResponse(success=False, message=f"Failed to resend: {str(e)}")

@router.post("/login", response_model=SuccessResponse)
async def login(login_data: UserLoginRequest):
    """User login"""
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
    else:
        if result.get("requires_verification"):
            return SuccessResponse(
                success=False,
                message=result["message"],
                data={"requires_verification": True}
            )
        return SuccessResponse(success=False, message=result["message"])

@router.get("/check-verification/{email}", response_model=SuccessResponse)
async def check_verification(email: str):
    """Check if user's email is verified"""
    try:
        user = database_service.get_user_by_email(email)
        if not user:
            return SuccessResponse(success=False, message="User not found")
        
        return SuccessResponse(
            success=True,
            message="Verification status retrieved",
            data={
                "email_verified": user.get('email_verified', False),
                "email": user['email'],
                "user_id": user['id']
            }
        )
    except Exception as e:
        return SuccessResponse(success=False, message=f"Check failed: {str(e)}")

# ========== SMS OTP Endpoints (Updated to work with KYC table) ==========

def get_kyc_by_user_id(user_id: str):
    """Get KYC info for user from database"""
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
    """Set OTP for phone verification in KYC table"""
    try:
        updates = {
            'phone_verification_otp': otp_code,
            'phone_otp_expires_at': expires_at.isoformat(),
            'phone_otp_last_sent': datetime.now(timezone.utc).isoformat(),
            'phone_otp_attempts': 0,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Check if KYC record exists
        kyc_info = get_kyc_by_user_id(user_id)
        
        if kyc_info:
            # Update existing KYC record
            endpoint = f"/rest/v1/kyc_information?user_id=eq.{user_id}"
        else:
            # Create new KYC record (without full KYC data)
            updates['user_id'] = user_id
            updates['id_number'] = 'pending'
            updates['first_name'] = 'pending'
            updates['last_name'] = 'pending'
            updates['date_of_birth'] = '2000-01-01'
            updates['phone_number'] = 'pending'
            updates['address'] = 'pending'
            updates['bank_account_number'] = 'pending'
            updates['bank_name'] = 'pending'
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
    """Verify phone OTP against database"""
    try:
        kyc_info = get_kyc_by_user_id(user_id)
        if not kyc_info:
            return {"success": False, "error": "KYC information not found"}
        
        # Check if already verified
        if kyc_info.get('phone_verified'):
            return {"success": True, "already_verified": True}
        
        # Check attempts
        attempts = kyc_info.get('phone_otp_attempts', 0)
        if attempts >= settings.otp_max_attempts:
            return {"success": False, "error": "Too many attempts. Please request a new OTP."}
        
        # Get stored OTP and expiry
        stored_otp = kyc_info.get('phone_verification_otp')
        stored_expiry = kyc_info.get('phone_otp_expires_at')
        
        if not stored_otp or not stored_expiry:
            return {"success": False, "error": "No OTP found. Please request a new one."}
        
        # Verify OTP
        if otp_service.is_otp_valid(stored_otp, stored_expiry, otp_code):
            # Mark phone as verified
            updates = {
                'phone_verified': True,
                'phone_verification_otp': None,
                'phone_otp_expires_at': None,
                'phone_otp_attempts': 0,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            endpoint = f"/rest/v1/kyc_information?user_id=eq.{user_id}"
            database_service.supabase.make_request(
                "PATCH", endpoint, updates, database_service.supabase.service_headers
            )
            
            return {
                "success": True,
                "verified": True,
                "user_id": user_id
            }
        else:
            # Increment attempt counter
            updates = {
                'phone_otp_attempts': attempts + 1,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            endpoint = f"/rest/v1/kyc_information?user_id=eq.{user_id}"
            database_service.supabase.make_request(
                "PATCH", endpoint, updates, database_service.supabase.service_headers
            )
            
            remaining_attempts = settings.otp_max_attempts - (attempts + 1)
            error_msg = "Invalid OTP code"
            if remaining_attempts <= 0:
                error_msg = "Too many failed attempts. Please request a new OTP."
            
            return {
                "success": False,
                "error": error_msg,
                "remaining_attempts": remaining_attempts,
                "user_id": user_id
            }
            
    except Exception as e:
        logger.error(f"Error verifying OTP: {e}")
        return {
            "success": False,
            "error": f"Verification failed: {str(e)}",
            "user_id": user_id
        }

def can_resend_otp(last_sent) -> bool:
    """Check if OTP can be resent"""
    try:
        if not last_sent:
            return True
        
        if isinstance(last_sent, str):
            last_sent = datetime.fromisoformat(last_sent.replace('Z', '+00:00'))
        
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)
        
        time_since_last = datetime.now(timezone.utc) - last_sent
        return time_since_last.total_seconds() >= settings.otp_resend_delay_seconds
        
    except Exception as e:
        logger.error(f"Error checking resend eligibility: {e}")
        return True

@router.post("/send-phone-otp", response_model=SuccessResponse)
async def send_phone_otp(
    request: SendOTPRequest,
    background_tasks: BackgroundTasks
):
    """Send OTP to phone number for verification"""
    try:
        user = database_service.get_user_by_id(request.user_id)
        if not user:
            return SuccessResponse(
                success=False,
                message="User not found",
                data={"user_id": request.user_id}
            )
        
        # Get KYC info
        kyc_info = get_kyc_by_user_id(request.user_id)
        
        # Check if phone is already verified
        if kyc_info and kyc_info.get('phone_verified'):
            return SuccessResponse(
                success=True,
                message="Phone already verified",
                data={
                    "already_verified": True,
                    "user_id": request.user_id
                }
            )
        
        # Check resend delay
        last_sent = kyc_info.get('phone_otp_last_sent') if kyc_info else None
        if last_sent and not can_resend_otp(last_sent):
            return SuccessResponse(
                success=False,
                message="Please wait 60 seconds before requesting a new OTP",
                data={"user_id": request.user_id}
            )
        
        # Generate OTP
        otp_code = otp_service.generate_otp()
        expires_at = otp_service.get_otp_expiry()
        
        # Store OTP in database
        success = set_phone_otp(request.user_id, otp_code, expires_at)
        if not success:
            return SuccessResponse(
                success=False,
                message="Failed to generate OTP",
                data={"user_id": request.user_id}
            )
        
        # Send SMS in background
        background_tasks.add_task(
            sms_service.send_otp_sms,
            request.phone_number,
            otp_code,
            user.get('full_name', 'User')
        )
        
        return SuccessResponse(
            success=True,
            message=f"OTP sent to {request.phone_number}",
            data={
                "expires_in_minutes": settings.otp_expiry_minutes,
                "user_id": request.user_id,
                "phone_number": request.phone_number,
                "simulated": sms_service.initialized and not settings.debug
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to send OTP: {e}")
        return SuccessResponse(
            success=False,
            message=f"Failed to send OTP: {str(e)}",
            data={"user_id": request.user_id}
        )

@router.post("/verify-phone-otp", response_model=SuccessResponse)
async def verify_phone_otp(request: VerifyOTPRequest):
    """Verify phone OTP"""
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
    else:
        return SuccessResponse(
            success=False,
            message=result.get("error", "Verification failed"),
            data={
                "remaining_attempts": result.get("remaining_attempts"),
                "user_id": request.user_id
            }
        )

@router.post("/resend-phone-otp", response_model=SuccessResponse)
async def resend_phone_otp(
    request: ResendOTPRequest,
    background_tasks: BackgroundTasks
):
    """Resend phone OTP"""
    try:
        user = database_service.get_user_by_id(request.user_id)
        if not user:
            return SuccessResponse(
                success=False,
                message="User not found",
                data={"user_id": request.user_id}
            )
        
        # Get KYC info
        kyc_info = get_kyc_by_user_id(request.user_id)
        if not kyc_info:
            return SuccessResponse(
                success=False,
                message="KYC information not found",
                data={"user_id": request.user_id}
            )
        
        # Check if already verified
        if kyc_info.get('phone_verified'):
            return SuccessResponse(
                success=True,
                message="Phone already verified",
                data={"already_verified": True}
            )
        
        # Check resend delay
        last_sent = kyc_info.get('phone_otp_last_sent')
        if last_sent and not can_resend_otp(last_sent):
            return SuccessResponse(
                success=False,
                message="Please wait 60 seconds before requesting a new OTP",
                data={"user_id": request.user_id}
            )
        
        # Generate new OTP
        otp_code = otp_service.generate_otp()
        expires_at = otp_service.get_otp_expiry()
        
        # Store OTP in database
        success = set_phone_otp(request.user_id, otp_code, expires_at)
        if not success:
            return SuccessResponse(
                success=False,
                message="Failed to generate OTP",
                data={"user_id": request.user_id}
            )
        
        # Get phone number from KYC or user
        phone_number = kyc_info.get('phone_number') or user.get('phone_number')
        if not phone_number:
            return SuccessResponse(
                success=False,
                message="Phone number not found",
                data={"user_id": request.user_id}
            )
        
        # Resend SMS
        background_tasks.add_task(
            sms_service.send_otp_sms,
            phone_number,
            otp_code,
            user.get('full_name', 'User')
        )
        
        return SuccessResponse(
            success=True,
            message="OTP resent successfully",
            data={
                "expires_in_minutes": settings.otp_expiry_minutes,
                "user_id": request.user_id
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to resend OTP: {e}")
        return SuccessResponse(
            success=False,
            message=f"Failed to resend OTP: {str(e)}",
            data={"user_id": request.user_id}
        )

@router.get("/test-sms-connection", response_model=SuccessResponse)
async def test_sms_connection():
    """Test SMS service connection"""
    try:
        result = sms_service.test_connection()
        
        if result.get("success"):
            return SuccessResponse(
                success=True,
                message="SMS service is connected and working",
                data=result
            )
        else:
            return SuccessResponse(
                success=False,
                message=f"SMS service test failed: {result.get('error')}",
                data=result
            )
            
    except Exception as e:
        return SuccessResponse(
            success=False,
            message=f"SMS test failed: {str(e)}"
        )
    
@router.post("/admin/register", response_model=SuccessResponse)
async def register_admin(
    user_id: str,
    admin_user_id: str = Depends(verify_admin_token)  # Only existing admins can register new admins
):
    """Register a new admin (admin only)"""
    try:
        admin_data = {
            'user_id': user_id,
            'role': 'moderator',
            'permissions': ['read', 'write', 'verify']
        }
        
        endpoint = "/rest/v1/admins"
        response = database_service.supabase.make_request(
            "POST", endpoint, admin_data, database_service.supabase.service_headers
        )
        
        return SuccessResponse(
            success=True,
            message="Admin registered successfully",
            data={"admin_id": response[0]['id'] if response else None}
        )
    except Exception as e:
        return SuccessResponse(success=False, message=str(e))