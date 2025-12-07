"""
OTP Service
"""

import random
import string
from datetime import datetime, timedelta, timezone
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class OTPService:
    def __init__(self):
        self.otp_length = 6

    # ---------------------------------------------------------
    # OTP Generate / Expire / Validate
    # ---------------------------------------------------------
    def generate_otp(self) -> str:
        return "".join(random.choices(string.digits, k=self.otp_length))

    def get_otp_expiry(self) -> datetime:
        return datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expiry_minutes)

    def is_otp_valid(self, stored_otp: str, stored_expiry, user_otp: str) -> bool:
        try:
            if not stored_otp or not stored_expiry or not user_otp:
                return False

            if isinstance(stored_expiry, str):
                stored_expiry = datetime.fromisoformat(stored_expiry.replace("Z", "+00:00"))

            if stored_expiry.tzinfo is None:
                stored_expiry = stored_expiry.replace(tzinfo=timezone.utc)

            if stored_expiry < datetime.now(timezone.utc):
                return False

            return stored_otp.strip() == user_otp.strip()

        except Exception as e:
            logger.error(f"OTP validation error: {e}")
            return False


otp_service = OTPService()
