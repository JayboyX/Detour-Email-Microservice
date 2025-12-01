# app/api/auth.py - UPDATE THE IMPORTS AND INITIALIZATION
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import Dict, Any
from datetime import datetime, timedelta
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
        expires_at = datetime.utcnow() + timedelta(hours=settings.verification_token_expire_hours)
        
        # Save verification token to database
        db_service.set_verification_token(user.id, verification_token, expires_at)
        
        # Create verification URL (deep link for mobile app)
        verification_url = f"{settings.app_scheme}://verify-email?token={verification_token}"
        
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
                message="Email already verified"
            )
        
        # Check if token matches and not expired
        if user.verification_token != request.token:
            return SuccessResponse(
                success=False,
                message="Invalid verification token"
            )
        
        if user.token_expires_at and user.token_expires_at < datetime.utcnow():
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
                    "email": user.email
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
        expires_at = datetime.utcnow() + timedelta(hours=settings.verification_token_expire_hours)
        
        # Save new token
        db_service.set_verification_token(user.id, verification_token, expires_at)
        
        # Create verification URL
        verification_url = f"{settings.app_scheme}://verify-email?token={verification_token}"
        
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