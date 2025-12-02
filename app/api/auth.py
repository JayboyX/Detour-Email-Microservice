# app/api/auth.py - UPDATED WITH TIMEZONE FIX
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import Dict, Any
from datetime import datetime, timedelta, timezone
import uuid

from app.supabase_client import get_supabase
from app.schemas import (
    UserCreateRequest, UserLoginRequest, VerifyEmailRequest,
    ResendVerificationRequest, SuccessResponse
)
from app.database_service import DatabaseService
from app.auth_service import AuthService
from app.email_service import EmailService
from app.config import settings

from app.sms_service import sms_service
from app.otp_service import otp_service
from app.sms_schemas import SendOTPRequest, VerifyOTPRequest, ResendOTPRequest

router = APIRouter()

# Initialize services
auth_service = AuthService()
email_service = EmailService()

@router.post("/signup", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def signup(
    user_data: UserCreateRequest,
    background_tasks: BackgroundTasks,
    supabase=Depends(get_supabase)  # Use the same client
):
    """
    Register a new user and send verification email
    """
    try:
        # Initialize database service
        db_service = DatabaseService(supabase, auth_service)
        
        # Check if user already exists
        if db_service.check_email_exists(user_data.email):
            return SuccessResponse(
                success=False,
                message="Email already registered"
            )
        
        # Create user
        user_dict = user_data.dict()
        user = db_service.create_user(user_dict)
        
        if not user:
            return SuccessResponse(
                success=False,
                message="Failed to create user account"
            )
        
        # Generate verification token
        verification_token = auth_service.create_verification_token(user.id, user.email)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.verification_token_expire_hours)
        
        # Save verification token to database
        db_service.set_verification_token(user.id, verification_token, expires_at)
        
        # Create verification URL (HTTP URL for web browser)
        verification_url = f"{settings.api_base_url}/verify-email?token={verification_token}"
        
        # Send verification email in background
        background_tasks.add_task(
            email_service.send_verification_email,
            user.email,
            verification_url,
            user.full_name
        )
        
        return SuccessResponse(
            success=True,
            message="Account created successfully! Please check your email for verification.",
            data={
                "user_id": user.id,
                "email": user.email,
                "requires_verification": True
            }
        )
        
    except Exception as e:
        return SuccessResponse(
            success=False,
            message=f"Registration failed: {str(e)}"
        )


@router.post("/verify-email", response_model=SuccessResponse)
def verify_email(
    request: VerifyEmailRequest,
    supabase=Depends(get_supabase)  # Use anon client for verification
):
    """
    Verify email using JWT token
    """
    try:
        # Decode and validate token
        payload = auth_service.decode_token(request.token)
        
        if not payload:
            return SuccessResponse(
                success=False,
                message="Invalid or expired verification token"
            )
        
        if payload.get("purpose") != "email_verification":
            return SuccessResponse(
                success=False,
                message="Invalid token type"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            return SuccessResponse(
                success=False,
                message="Invalid token payload"
            )
        
        # Initialize database service
        db_service = DatabaseService(supabase, auth_service)
        
        # Get user
        user = db_service.get_user_by_id(user_id)
        if not user:
            return SuccessResponse(
                success=False,
                message="User not found"
            )
        
        # Check if already verified
        if user.email_verified:
            return SuccessResponse(
                success=True,
                message="Email already verified",
                data={
                    "user_id": user_id,
                    "email": user.email,
                    "already_verified": True
                }
            )
        
        # Check if token matches and not expired
        if user.verification_token != request.token:
            return SuccessResponse(
                success=False,
                message="Invalid verification token"
            )
        
        # Fix timezone comparison
        if user.token_expires_at:
            # Ensure both datetimes are timezone-aware for comparison
            expires_at = user.token_expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            if expires_at < datetime.now(timezone.utc):
                return SuccessResponse(
                    success=False,
                    message="Verification token has expired. Please request a new one."
                )
        
        # Verify email
        success = db_service.verify_email(user_id)
        
        if success:
            return SuccessResponse(
                success=True,
                message="Email verified successfully! You can now log in to your account.",
                data={
                    "user_id": user_id,
                    "email": user.email,
                    "verified": True
                }
            )
        else:
            return SuccessResponse(
                success=False,
                message="Failed to verify email"
            )
            
    except Exception as e:
        return SuccessResponse(
            success=False,
            message=f"Verification failed: {str(e)}"
        )

@router.post("/resend-verification", response_model=SuccessResponse)
def resend_verification(
    request: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    supabase=Depends(get_supabase)
):
    """
    Resend verification email
    """
    try:
        # Initialize services
        db_service = DatabaseService(supabase, auth_service)
        
        # Get user
        user = db_service.get_user_by_email(request.email)
        if not user:
            return SuccessResponse(
                success=False,
                message="User not found"
            )
        
        if user.email_verified:
            return SuccessResponse(
                success=False,
                message="Email already verified"
            )
        
        # Generate new verification token
        verification_token = auth_service.create_verification_token(user.id, user.email)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.verification_token_expire_hours)
        
        # Save new token
        db_service.set_verification_token(user.id, verification_token, expires_at)
        
        # Create verification URL (HTTP URL for web browser)
        verification_url = f"{settings.api_base_url}/verify-email?token={verification_token}"
        
        # Resend email in background
        background_tasks.add_task(
            email_service.send_verification_email,
            user.email,
            verification_url,
            user.full_name
        )
        
        return SuccessResponse(
            success=True,
            message="Verification email resent successfully. Please check your inbox."
        )
        
    except Exception as e:
        return SuccessResponse(
            success=False,
            message=f"Failed to resend verification: {str(e)}"
        )

@router.post("/login", response_model=SuccessResponse)
def login(
    login_data: UserLoginRequest,
    supabase=Depends(get_supabase)
):
    """
    User login - checks if email is verified
    """
    try:
        # Initialize services
        db_service = DatabaseService(supabase, auth_service)
        
        # Get user
        user = db_service.get_user_by_email(login_data.email)
        
        if not user:
            return SuccessResponse(
                success=False,
                message="Invalid email or password"
            )
        
        # Check password
        if not user.password_hash or not auth_service.verify_password(login_data.password, user.password_hash):
            return SuccessResponse(
                success=False,
                message="Invalid email or password"
            )
        
        # Check if email is verified
        if not user.email_verified:
            return SuccessResponse(
                success=False,
                message="Email not verified. Please check your email for the verification link.",
                data={
                    "requires_verification": True,
                    "email": user.email
                }
            )
        
        # Generate access token
        access_token = auth_service.create_access_token(user.id)
        
        return SuccessResponse(
            success=True,
            message="Login successful",
            data={
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "email_verified": user.email_verified
                }
            }
        )
        
    except Exception as e:
        return SuccessResponse(
            success=False,
            message=f"Login failed: {str(e)}"
        )

@router.get("/check-verification/{email}", response_model=SuccessResponse)
def check_verification(
    email: str,
    supabase=Depends(get_supabase)
):
    """
    Check if user's email is verified
    """
    try:
        db_service = DatabaseService(supabase, auth_service)
        user = db_service.get_user_by_email(email)
        
        if not user:
            return SuccessResponse(
                success=False,
                message="User not found"
            )
        
        return SuccessResponse(
            success=True,
            message="Verification status retrieved",
            data={
                "email_verified": user.email_verified,
                "email": user.email,
                "user_id": user.id
            }
        )
        
    except Exception as e:
        return SuccessResponse(
            success=False,
            message=f"Check failed: {str(e)}"
        )
    
    
@router.post("/send-phone-otp", response_model=SuccessResponse)
def send_phone_otp(
    request: SendOTPRequest,
    background_tasks: BackgroundTasks,
    supabase=Depends(get_supabase)
):
    """Send OTP to phone number for verification"""
    try:
        # Initialize services
        db_service = DatabaseService(supabase, auth_service)
        
        # Get user
        user = db_service.get_user_by_id(request.user_id)
        if not user:
            return SuccessResponse(
                success=False,
                message="User not found"
            )
        
        # Get KYC info
        kyc_info = db_service.get_kyc_by_user_id(request.user_id)
        if not kyc_info:
            return SuccessResponse(
                success=False,
                message="KYC information not found. Please complete KYC first."
            )
        
        # Check if phone is already verified
        if kyc_info.get('phone_verified'):
            return SuccessResponse(
                success=True,
                message="Phone already verified",
                data={"already_verified": True}
            )
        
        # Check resend delay
        last_sent = kyc_info.get('phone_otp_last_sent')
        if last_sent and isinstance(last_sent, str):
            last_sent = datetime.fromisoformat(last_sent.replace('Z', '+00:00'))
        
        if not otp_service.can_resend_otp(last_sent):
            return SuccessResponse(
                success=False,
                message="Please wait before requesting a new OTP"
            )
        
        # Generate OTP
        otp_code = otp_service.generate_otp()
        expires_at = otp_service.get_otp_expiry()
        
        # Store OTP in database
        success = db_service.set_phone_otp(request.user_id, otp_code, expires_at)
        if not success:
            return SuccessResponse(
                success=False,
                message="Failed to generate OTP"
            )
        
        # Send SMS in background
        background_tasks.add_task(
            sms_service.send_otp_sms,
            request.phone_number,
            otp_code,
            user.full_name
        )
        
        return SuccessResponse(
            success=True,
            message=f"OTP sent to {request.phone_number}",
            data={
                "expires_in_minutes": settings.otp_expiry_minutes,
                "user_id": request.user_id
            }
        )
        
    except Exception as e:
        return SuccessResponse(
            success=False,
            message=f"Failed to send OTP: {str(e)}"
        )

@router.post("/verify-phone-otp", response_model=SuccessResponse)
def verify_phone_otp(
    request: VerifyOTPRequest,
    supabase=Depends(get_supabase)
):
    """Verify phone OTP"""
    try:
        db_service = DatabaseService(supabase, auth_service)
        
        # Verify OTP
        result = db_service.verify_phone_otp(request.user_id, request.otp_code)
        
        if result.get("success"):
            return SuccessResponse(
                success=True,
                message="Phone number verified successfully",
                data={"verified": True}
            )
        else:
            return SuccessResponse(
                success=False,
                message=result.get("error", "Verification failed"),
                data=result
            )
            
    except Exception as e:
        return SuccessResponse(
            success=False,
            message=f"Verification failed: {str(e)}"
        )

@router.get("/check-phone-verification/{user_id}", response_model=SuccessResponse)
def check_phone_verification(
    user_id: str,
    supabase=Depends(get_supabase)
):
    """Check phone verification status"""
    try:
        db_service = DatabaseService(supabase, auth_service)
        
        # Get KYC info
        kyc_info = db_service.get_kyc_by_user_id(user_id)
        if not kyc_info:
            return SuccessResponse(
                success=False,
                message="KYC information not found"
            )
        
        phone_verified = kyc_info.get('phone_verified', False)
        phone_number = kyc_info.get('phone_number')
        
        return SuccessResponse(
            success=True,
            message="Verification status retrieved",
            data={
                "phone_verified": phone_verified,
                "phone_number": phone_number,
                "user_id": user_id
            }
        )
        
    except Exception as e:
        return SuccessResponse(
            success=False,
            message=f"Check failed: {str(e)}"
        )