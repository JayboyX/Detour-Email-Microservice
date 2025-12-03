"""
Main authentication router
Combines email, SMS, and user authentication
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from typing import Dict, Any
from datetime import datetime, timedelta, timezone

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

# ========== SMS OTP Endpoints ==========
@router.post("/send-phone-otp", response_model=SuccessResponse)
async def send_phone_otp(
    request: SendOTPRequest,
    background_tasks: BackgroundTasks
):
    """Send OTP to phone number for verification"""
    try:
        user = database_service.get_user_by_id(request.user_id)
        if not user:
            return SuccessResponse(success=False, message="User not found")
        
        # Generate OTP
        otp_code = otp_service.generate_otp()
        
        # TODO: Implement OTP storage in database
        # For now, just send SMS
        
        # Send SMS in background
        background_tasks.add_task(
            sms_service.send_otp_sms,
            request.phone_number,
            otp_code,
            user['full_name']
        )
        
        return SuccessResponse(
            success=True,
            message=f"OTP sent to {request.phone_number}",
            data={
                "expires_in_minutes": settings.otp_expiry_minutes,
                "user_id": request.user_id,
                "simulated": sms_service.initialized and not settings.debug
            }
        )
        
    except Exception as e:
        return SuccessResponse(success=False, message=f"Failed to send OTP: {str(e)}")

@router.get("/test-sms-connection", response_model=SuccessResponse)
async def test_sms_connection():
    """Test SMS service connection"""
    result = sms_service.test_connection()
    
    if result.get("success"):
        return SuccessResponse(
            success=True,
            message="SMS service is connected",
            data=result
        )
    else:
        return SuccessResponse(
            success=False,
            message=f"SMS service test failed: {result.get('error')}",
            data=result
        )