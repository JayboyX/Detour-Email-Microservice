from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

# Pydantic models for Supabase
class UserCreate(BaseModel):
    full_name: str
    email: str
    password: str
    terms_agreed: bool
    phone_number: Optional[str] = None

class UserInDB(BaseModel):
    id: str
    full_name: str
    email: str
    password_hash: Optional[str] = None
    phone_number: Optional[str] = None
    profile_photo_url: Optional[str] = None
    terms_agreed: bool = False
    is_kyc_verified: bool = False
    google_id: Optional[str] = None
    facebook_id: Optional[str] = None
    created_at: datetime
    email_verified: bool = False
    verification_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    
    @classmethod
    def from_supabase(cls, data: Dict[str, Any]) -> 'UserInDB':
        """Create UserInDB from Supabase response"""
        return cls(
            id=str(data.get('id', '')),
            full_name=data.get('full_name', ''),
            email=data.get('email', ''),
            password_hash=data.get('password_hash'),
            phone_number=data.get('phone_number'),
            profile_photo_url=data.get('profile_photo_url'),
            terms_agreed=data.get('terms_agreed', False),
            is_kyc_verified=data.get('is_kyc_verified', False),
            google_id=data.get('google_id'),
            facebook_id=data.get('facebook_id'),
            created_at=data.get('created_at'),
            email_verified=data.get('email_verified', False),
            verification_token=data.get('verification_token'),
            token_expires_at=data.get('token_expires_at')
        )

class UserResponse(BaseModel):
    id: str
    full_name: str
    email: str
    email_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True