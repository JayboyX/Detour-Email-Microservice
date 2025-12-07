"""
SMS Service (WinSMS)
"""

import os
import urllib.parse
import logging
from datetime import datetime, timezone
from typing import Dict, Any
import httpx
import json

from app.config import settings

logger = logging.getLogger(__name__)


class SMSService:
    def __init__(self):
        self.sms_user = os.getenv("SMS_USER", settings.sms_user)
        self.sms_password = os.getenv("SMS_PASSWORD", settings.sms_password)
        self.api_url = settings.sms_api_url

        if not self.sms_user or not self.sms_password:
            logger.warning("SMS credentials missing")
            self.initialized = False
        else:
            self.initialized = True
            logger.info("SMS Service initialized")

    # ---------------------------------------------------------
    # Public Entry (Unified OTP Sender)
    # ---------------------------------------------------------
    def send_otp_sms(self, phone_number: str, otp_code: str, user_name: str = "User") -> Dict[str, Any]:
        try:
            cleaned = self._clean_phone_number(phone_number)

            if not self._validate_phone_number(cleaned):
                return {"success": False, "error": "Invalid phone number", "simulated": True}

            message = (
                f"Your Detour verification code is: {otp_code}. "
                f"Valid for {settings.otp_expiry_minutes} minutes."
            )

            # REAL SEND if initialized
            if self.initialized:

                # Debug → log only
                if settings.debug:
                    return self._debug_send(cleaned, otp_code, message)

                # Try real SMS
                result = self._send_via_winsms(cleaned, message)

                # Fallback → debug
                if not result["success"]:
                    logger.warning(f"SMSGateway failed, fallback to debug → {result.get('error')}")
                    return self._debug_send(cleaned, otp_code, message)

                return result

            # No credentials → debug mode
            return self._debug_send(cleaned, otp_code, message)

        except Exception as e:
            logger.error(f"SMS error: {e}")
            return self._debug_send(phone_number, otp_code, str(e))

    # ---------------------------------------------------------
    # Phone Utilities
    # ---------------------------------------------------------
    def _clean_phone_number(self, phone_number: str) -> str:
        digits = "".join(filter(str.isdigit, phone_number))
        if digits.startswith("27"):
            return digits
        if digits.startswith("0"):
            return "27" + digits[1:]
        return digits

    def _validate_phone_number(self, phone_number: str) -> bool:
        digits = "".join(filter(str.isdigit, phone_number))
        return len(digits) == 11 and digits.startswith("27")

    # ---------------------------------------------------------
    # WinSMS Sender
    # ---------------------------------------------------------
    def _send_via_winsms(self, phone_number: str, message: str) -> Dict[str, Any]:
        try:
            params = {
                "User": self.sms_user,
                "Password": self.sms_password,
                "Message": message,
                "Numbers": phone_number,
            }

            url = f"{self.api_url.rstrip('/')}?{urllib.parse.urlencode(params)}"

            with httpx.Client(timeout=30.0) as client:
                response = client.get(url)
                response_text = response.text.strip()

            # Response parsing
            if "=" in response_text:
                _, result = response_text.split("=", 1)
                result = result.replace("&", "").strip()

                known_errors = {
                    "INSUFFICIENT CREDITS": "Insufficient SMS credits",
                    "ACCOUNTLOCKED": "SMS account locked",
                    "BADDEST": "Invalid phone number",
                    "INVALIDUSER": "Invalid SMS credentials",
                    "NOCREDIT": "No credit available",
                }

                if result in known_errors:
                    return {"success": False, "error": known_errors[result], "simulated": False}

                return {
                    "success": True,
                    "message_id": result,
                    "phone_number": phone_number,
                    "simulated": False,
                }

            return {"success": False, "error": f"Unexpected response: {response_text}", "simulated": False}

        except httpx.RequestError as e:
            return {"success": False, "error": f"Network error: {e}", "simulated": False}

    # ---------------------------------------------------------
    # Debug SMS Logger
    # ---------------------------------------------------------
    def _debug_send(self, phone_number: str, otp_code: str, message: str) -> Dict[str, Any]:
        debug = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "DEBUG" if settings.debug else "FALLBACK",
            "phone_number": phone_number,
            "otp": otp_code,
        }

        print("\n" + "=" * 60)
        print(f"📱 SMS DEBUG → {phone_number}")
        print(f"OTP: {otp_code}")
        print("=" * 60 + "\n")

        try:
            with open("logs/sms_debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(debug, indent=2))
                f.write("\n" + ("-" * 50) + "\n")
        except Exception as e:
            logger.error(f"SMS debug logging failed: {e}")

        return {"success": True, "simulated": True, "phone_number": phone_number}

    # ---------------------------------------------------------
    # Connection Test
    # ---------------------------------------------------------
    def test_connection(self) -> Dict[str, Any]:
        if not self.initialized:
            return {"success": False, "error": "SMS credentials not configured"}

        try:
            test = self._send_via_winsms("27721234567", "Test SMS from Detour API")
            return {"success": test["success"], "error": test.get("error"), "initialized": True}
        except Exception as e:
            return {"success": False, "error": str(e)}


sms_service = SMSService()
