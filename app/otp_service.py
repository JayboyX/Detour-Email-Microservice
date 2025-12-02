"""
OTP Generation and Verification Service
"""
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging
from app.config import settings

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
        try:
            if not all([stored_otp, stored_expiry, user_otp]):
                return False
            
            # Check if stored_expiry is string, convert to datetime
            if isinstance(stored_expiry, str):
                stored_expiry = datetime.fromisoformat(stored_expiry.replace('Z', '+00:00'))
            
            # Ensure stored_expiry is timezone aware
            if stored_expiry.tzinfo is None:
                stored_expiry = stored_expiry.replace(tzinfo=timezone.utc)
            
            # Check expiry
            if stored_expiry < datetime.now(timezone.utc):
                logger.warning("OTP has expired")
                return False
            
            # Compare OTPs (case-insensitive, strip whitespace)
            return stored_otp.strip() == user_otp.strip()
            
        except Exception as e:
            logger.error(f"Error validating OTP: {e}")
            return False
    
    def can_resend_otp(self, last_sent: Optional[datetime]) -> bool:
        """Check if OTP can be resent"""
        try:
            if not last_sent:
                return True
            
            # Convert to datetime if string
            if isinstance(last_sent, str):
                last_sent = datetime.fromisoformat(last_sent.replace('Z', '+00:00'))
            
            # Ensure last_sent is timezone aware
            if last_sent.tzinfo is None:
                last_sent = last_sent.replace(tzinfo=timezone.utc)
            
            # Calculate time since last sent
            time_since_last = datetime.now(timezone.utc) - last_sent
            return time_since_last.total_seconds() >= settings.otp_resend_delay_seconds
            
        except Exception as e:
            logger.error(f"Error checking resend eligibility: {e}")
            return True


# Create global instance
otp_service = OTPService()