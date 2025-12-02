"""
Pydantic schemas for SMS OTP operations
"""
from pydantic import BaseModel, validator
import re

# Phone validation regex
PHONE_REGEX = re.compile(r'^\+?[1-9]\d{1,14}$')

class SendOTPRequest(BaseModel):
    user_id: str
    phone_number: str
    
    @validator('phone_number')
    def validate_phone(cls, v):
        # Basic phone validation
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