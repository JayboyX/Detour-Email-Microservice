"""
OTP Generation and Verification Service
"""
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging
from app.config import settings  # Missing import!

logger = logging.getLogger(__name__)

class OTPService:
    """Generate and verify OTP codes"""
    
    def __init__(self):
        self.otp_length = 6
    
    def generate_otp(self) -> str:
        """Generate a 6-digit OTP"""
        return ''.join(random.choices(string.digits, k=self.otp_length))
    
    def get_otp_expiry(self) -> datetime:
        """Get OTP expiry datetime"""
        return datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expiry_minutes)
    
    def is_otp_valid(self, stored_otp: str, stored_expiry: datetime, user_otp: str) -> bool:
        """Verify if OTP is valid"""
        if not all([stored_otp, stored_expiry, user_otp]):
            return False
        
        # Check expiry
        if stored_expiry < datetime.now(timezone.utc):
            logger.warning("OTP has expired")
            return False
        
        # Compare OTPs (case-insensitive)
        return stored_otp.strip() == user_otp.strip()
    
    def can_resend_otp(self, last_sent: Optional[datetime]) -> bool:
        """Check if OTP can be resent"""
        if not last_sent:
            return True
        
        # Calculate time since last sent
        time_since_last = datetime.now(timezone.utc) - last_sent
        return time_since_last.total_seconds() >= settings.otp_resend_delay_seconds


# Create global instance
otp_service = OTPService()