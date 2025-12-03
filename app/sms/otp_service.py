"""
OTP Service for SMS
"""
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class OTPService:
    def __init__(self):
        self.otp_length = 6
    
    def generate_otp(self) -> str:
        """Generate a 6-digit OTP"""
        return ''.join(random.choices(string.digits, k=self.otp_length))
    
    def get_otp_expiry(self) -> datetime:
        """Get OTP expiry datetime"""
        return datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expiry_minutes)
    
    def is_otp_valid(self, stored_otp: str, stored_expiry, user_otp: str) -> bool:
        """Verify if OTP is valid"""
        try:
            if not all([stored_otp, stored_expiry, user_otp]):
                return False
            
            if isinstance(stored_expiry, str):
                stored_expiry = datetime.fromisoformat(stored_expiry.replace('Z', '+00:00'))
            
            if stored_expiry.tzinfo is None:
                stored_expiry = stored_expiry.replace(tzinfo=timezone.utc)
            
            if stored_expiry < datetime.now(timezone.utc):
                return False
            
            return stored_otp.strip() == user_otp.strip()
            
        except Exception as e:
            logger.error(f"Error validating OTP: {e}")
            return False

# Create global instance
otp_service = OTPService()