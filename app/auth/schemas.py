"""
Authentication Schemas
"""

from pydantic import BaseModel, validator, Field
from typing import Optional
from datetime import datetime
import re

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


# ---------------------------------------------------------
# User Registration & Login
# ---------------------------------------------------------
class UserCreateRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: str
    password: str = Field(..., min_length=6, max_length=72)
    terms_agreed: bool
    phone_number: Optional[str] = Field(None, min_length=10, max_length=20)

    @validator("email")
    def validate_email(cls, v):
        if not EMAIL_REGEX.match(v):
            raise ValueError("Invalid email format")
        return v.lower()

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        if len(v) > 72:
            raise ValueError("Password cannot exceed 72 characters")
        return v

    @validator("phone_number")
    def validate_phone(cls, v):
        if v:
            digits = "".join(filter(str.isdigit, v))
            if len(digits) < 10:
                raise ValueError("Invalid phone number format")
        return v


class UserLoginRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=6, max_length=72)

    @validator("email")
    def validate_email(cls, v):
        if not EMAIL_REGEX.match(v):
            raise ValueError("Invalid email format")
        return v.lower()

    @validator("password")
    def validate_password(cls, v):
        if len(v) > 72:
            v = v[:72]
        return v


# ---------------------------------------------------------
# Email Verification
# ---------------------------------------------------------
class VerifyEmailRequest(BaseModel):
    token: str = Field(..., min_length=10)


class ResendVerificationRequest(BaseModel):
    email: str

    @validator("email")
    def validate_email(cls, v):
        if not EMAIL_REGEX.match(v):
            raise ValueError("Invalid email format")
        return v.lower()


# ---------------------------------------------------------
# SMS OTP
# ---------------------------------------------------------
class SendOTPRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    phone_number: str = Field(..., min_length=10)

    @validator("phone_number")
    def validate_phone(cls, v):
        digits = "".join(filter(str.isdigit, v))
        if len(digits) < 10:
            raise ValueError("Invalid phone number format")
        return v


class VerifyOTPRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    otp_code: str = Field(..., min_length=6, max_length=6)

    @validator("otp_code")
    def validate_otp(cls, v):
        if not v.isdigit():
            raise ValueError("OTP must contain only digits")
        return v


class ResendOTPRequest(BaseModel):
    user_id: str = Field(..., min_length=1)


# ---------------------------------------------------------
# Response Models
# ---------------------------------------------------------
class SuccessResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[str] = None


# ---------------------------------------------------------
# Database Response Models
# ---------------------------------------------------------
class UserInDB(BaseModel):
    id: str
    full_name: str
    email: str
    password_hash: Optional[str] = None
    phone_number: Optional[str] = None
    terms_agreed: bool = False
    email_verified: bool = False
    verification_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    created_at: datetime

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=str(data.get("id", "")),
            full_name=data.get("full_name", ""),
            email=data.get("email", ""),
            password_hash=data.get("password_hash"),
            phone_number=data.get("phone_number"),
            terms_agreed=data.get("terms_agreed", False),
            email_verified=data.get("email_verified", False),
            verification_token=data.get("verification_token"),
            token_expires_at=data.get("token_expires_at"),
            created_at=data.get("created_at")
        )


class UserResponse(BaseModel):
    id: str
    full_name: str
    email: str
    email_verified: bool
    phone_number: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
