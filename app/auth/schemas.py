"""
Pydantic schemas for authentication
"""
from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
import re

# Email validation
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# Auth schemas
class UserCreateRequest(BaseModel):
    full_name: str
    email: str
    password: str
    terms_agreed: bool
    phone_number: Optional[str] = None
    
    @validator('email')
    def validate_email(cls, v):
        if not EMAIL_REGEX.match(v):
            raise ValueError('Invalid email format')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v

class UserLoginRequest(BaseModel):
    email: str
    password: str
    
    @validator('email')
    def validate_email(cls, v):
        if not EMAIL_REGEX.match(v):
            raise ValueError('Invalid email format')
        return v.lower()

class VerifyEmailRequest(BaseModel):
    token: str

class ResendVerificationRequest(BaseModel):
    email: str
    
    @validator('email')
    def validate_email(cls, v):
        if not EMAIL_REGEX.match(v):
            raise ValueError('Invalid email format')
        return v.lower()

# SMS schemas
class SendOTPRequest(BaseModel):
    user_id: str
    phone_number: str
    
    @validator('phone_number')
    def validate_phone(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError('Invalid phone number')
        return v.strip()

class VerifyOTPRequest(BaseModel):
    user_id: str
    otp_code: str
    
    @validator('otp_code')
    def validate_otp(cls, v):
        if not v or len(v.strip()) != 6 or not v.strip().isdigit():
            raise ValueError('OTP must be 6 digits')
        return v.strip()

class ResendOTPRequest(BaseModel):
    user_id: str

# Response schemas
class SuccessResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

# Database models
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
    def from_dict(cls, data: dict) -> 'UserInDB':
        """Create UserInDB from dictionary"""
        return cls(**data)

class UserResponse(BaseModel):
    id: str
    full_name: str
    email: str
    email_verified: bool
    created_at: datetime