"""
SMS Service using WinSMS API
"""
import os
import urllib.parse
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

class SMSService:
    """WinSMS service for sending OTP SMS messages"""
    
    def __init__(self):
        self.sms_user = settings.sms_user
        self.sms_password = settings.sms_password
        self.api_url = settings.sms_api_url
        
        # Validate credentials on init
        if not all([self.sms_user, self.sms_password]):
            logger.warning("SMS credentials not configured. SMS sending will be simulated.")
            self.initialized = False
        else:
            self.initialized = True
            logger.info("SMS Service initialized")
    
    def send_otp_sms(self, phone_number: str, otp_code: str, user_name: str = "User") -> Dict[str, Any]:
        """
        Send OTP SMS via WinSMS API
        
        Args:
            phone_number: User's phone number (with or without +)
            otp_code: 6-digit OTP code
            user_name: User's name for personalization
        
        Returns:
            Dictionary with success status and details
        """
        # Clean phone number
        cleaned_number = self._clean_phone_number(phone_number)
        
        if not self._validate_phone_number(cleaned_number):
            return {
                "success": False,
                "error": "Invalid phone number format",
                "simulated": True
            }
        
        # Create SMS message
        message = f"Your Detour verification code is: {otp_code}. Valid for {settings.otp_expiry_minutes} minutes."
        
        if not self.initialized or settings.debug:
            # Simulate sending in debug mode
            return self._debug_send(cleaned_number, otp_code, message)
        
        # Send via WinSMS API
        return self._send_via_winsms(cleaned_number, message)
    
    def _clean_phone_number(self, phone_number: str) -> str:
        """Clean and format phone number"""
        # Remove all non-digit characters except leading +
        cleaned = ''.join(c for c in phone_number if c.isdigit() or c == '+')
        
        # If starts with +, keep it, otherwise assume South African number
        if cleaned.startswith('+'):
            return cleaned.replace('+', '')  # WinSMS doesn't want +
        elif cleaned.startswith('0'):
            # Convert South African number to international format
            return '27' + cleaned[1:]  # +27XXXXXXXXX
        else:
            return cleaned
    
    def _validate_phone_number(self, phone_number: str) -> bool:
        """Validate phone number format"""
        # Remove all non-digits
        digits = ''.join(c for c in phone_number if c.isdigit())
        
        # Basic validation - should be at least 10 digits
        return len(digits) >= 10
    
    def _send_via_winsms(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send SMS via WinSMS API"""
        try:
            # Prepare query parameters
            params = {
                "user": self.sms_user,
                "password": self.sms_password,
                "message": message,
                "numbers": phone_number
            }
            
            # Build URL with query parameters
            query_string = urllib.parse.urlencode(params)
            url = f"{self.api_url}?{query_string}"
            
            # Make request
            response = httpx.get(url, timeout=30.0)
            response_text = response.text
            
            logger.info(f"SMS API Response: {response_text}")
            
            # Parse WinSMS response
            if "=" in response_text:
                _, result = response_text.split("=", 1)
                result = result.replace("&", "").strip()
                
                if result == "INSUFFICIENT CREDITS":
                    return {
                        "success": False,
                        "error": "SMS credits are insufficient",
                        "simulated": False
                    }
                elif result == "ACCOUNTLOCKED":
                    return {
                        "success": False,
                        "error": "SMS account is locked",
                        "simulated": False
                    }
                elif result == "BADDEST":
                    return {
                        "success": False,
                        "error": "Invalid phone number",
                        "simulated": False
                    }
                else:
                    # Success - returns message ID
                    return {
                        "success": True,
                        "message_id": result,
                        "simulated": False,
                        "phone_number": phone_number
                    }
            else:
                return {
                    "success": False,
                    "error": f"Unexpected API response: {response_text}",
                    "simulated": False
                }
                
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return {
                "success": False,
                "error": f"SMS sending failed: {str(e)}",
                "simulated": False
            }
    
    def _debug_send(self, phone_number: str, otp_code: str, message: str) -> Dict[str, Any]:
        """Simulate SMS sending in debug mode"""
        debug_info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "DEBUG",
            "phone_number": phone_number,
            "otp_code": otp_code,
            "message": message,
            "simulated": True
        }
        
        # Log to console
        print(f"\n{'='*60}")
        print(f"📱 DEBUG SMS")
        print(f"   To: {phone_number}")
        print(f"   OTP: {otp_code}")
        print(f"   Message: {message}")
        print(f"{'='*60}\n")
        
        # Log to file
        try:
            import json
            with open('sms_log.json', 'a', encoding='utf-8') as f:
                f.write(json.dumps(debug_info, indent=2))
                f.write('\n' + '-'*50 + '\n')
        except Exception as e:
            logger.error(f"Failed to write SMS log: {e}")
        
        return {
            "success": True,
            "simulated": True,
            "phone_number": phone_number,
            "otp_code": otp_code,
            "message": "SMS would be sent in production"
        }


# Create global instance
sms_service = SMSService()