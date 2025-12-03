"""
SMS Service using WinSMS API
"""
import os
import urllib.parse
import logging
from datetime import datetime, timezone
from typing import Dict, Any
import httpx
import json

from app.config import settings
from app.sms.otp_service import otp_service

logger = logging.getLogger(__name__)

class SMSService:
    def __init__(self):
        self.sms_user = os.getenv('SMS_USER', settings.sms_user)
        self.sms_password = os.getenv('SMS_PASSWORD', settings.sms_password)
        self.api_url = settings.sms_api_url
        
        if not self.sms_user or not self.sms_password:
            logger.warning("SMS credentials not configured")
            self.initialized = False
        else:
            self.initialized = True
            logger.info("✅ SMS Service ready")
    
    def send_otp_sms(self, phone_number: str, otp_code: str, user_name: str = "User") -> Dict[str, Any]:
        """Send OTP SMS via WinSMS API"""
        try:
            cleaned_number = self._clean_phone_number(phone_number)
            
            if not self._validate_phone_number(cleaned_number):
                return {
                    "success": False,
                    "error": "Invalid phone number",
                    "simulated": True
                }
            
            message = f"Your Detour verification code is: {otp_code}. Valid for {settings.otp_expiry_minutes} minutes."
            
            # CHANGE: Always try to send via WinSMS if initialized, regardless of debug mode
            # Debug mode only affects whether we log instead of sending
            if self.initialized:
                # If debug mode is ON, just log it
                if settings.debug:
                    return self._debug_send(cleaned_number, otp_code, message)
                
                # If debug mode is OFF, try to send real SMS
                result = self._send_via_winsms(cleaned_number, message)
                
                # If real SMS fails, fall back to debug mode
                if result["success"]:
                    return result
                else:
                    logger.warning(f"Real SMS failed, falling back to debug: {result.get('error')}")
                    return self._debug_send(cleaned_number, otp_code, message)
            
            # If SMS service not initialized, use debug mode
            return self._debug_send(cleaned_number, otp_code, message)
                
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return self._debug_send(phone_number, otp_code, f"Error: {str(e)}")
        
    def _clean_phone_number(self, phone_number: str) -> str:
        """Clean and format phone number"""
        digits = ''.join(filter(str.isdigit, phone_number))
        
        if digits.startswith('27'):
            return digits
        elif digits.startswith('0'):
            return '27' + digits[1:]
        else:
            return digits
    
    def _validate_phone_number(self, phone_number: str) -> bool:
        """Validate phone number format"""
        digits = ''.join(filter(str.isdigit, phone_number))
        return len(digits) == 11 and digits.startswith('27')
    
    def _send_via_winsms(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send SMS via WinSMS API"""
        try:
            params = {
                "User": self.sms_user,
                "Password": self.sms_password,
                "Message": message,
                "Numbers": phone_number
            }
            
            query_string = urllib.parse.urlencode(params)
            url = f"{self.api_url.rstrip('/')}?{query_string}"
            
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url)
                response_text = response.text.strip()
                
                if "=" in response_text:
                    parts = response_text.split("=", 1)
                    if len(parts) == 2:
                        _, result = parts
                        result = result.replace("&", "").strip()
                        
                        error_messages = {
                            "INSUFFICIENT CREDITS": "SMS credits are insufficient",
                            "ACCOUNTLOCKED": "SMS account is locked",
                            "BADDEST": "Invalid phone number",
                            "INVALIDUSER": "Invalid user credentials",
                            "NOCREDIT": "No credit available"
                        }
                        
                        if result in error_messages:
                            return {
                                "success": False,
                                "error": error_messages[result],
                                "simulated": False
                            }
                        else:
                            return {
                                "success": True,
                                "message_id": result,
                                "simulated": False,
                                "phone_number": phone_number
                            }
                
                return {
                    "success": False,
                    "error": f"Unexpected response: {response_text}",
                    "simulated": False
                }
                
        except httpx.RequestError as e:
            return {
                "success": False,
                "error": f"Network error: {str(e)}",
                "simulated": False
            }
    
    def _debug_send(self, phone_number: str, otp_code: str, message: str) -> Dict[str, Any]:
        """Debug mode - log instead of sending"""
        debug_info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "DEBUG" if settings.debug else "FALLBACK",
            "phone_number": phone_number,
            "otp_code": otp_code,
            "simulated": True
        }
        
        print(f"\n{'='*60}")
        print(f"📱 DEBUG SMS to: {phone_number}")
        print(f"   OTP: {otp_code}")
        print(f"{'='*60}\n")
        
        try:
            with open('logs/sms_debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps(debug_info, indent=2))
                f.write('\n' + '-'*50 + '\n')
        except Exception as e:
            logger.error(f"Failed to write SMS log: {e}")
        
        return {
            "success": True,
            "simulated": True,
            "phone_number": phone_number,
            "otp_code": otp_code
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """Test SMS connection"""
        try:
            if not self.initialized:
                return {
                    "success": False,
                    "error": "SMS credentials not configured"
                }
            
            test_result = self._send_via_winsms("27721234567", "Test SMS from Detour API")
            
            return {
                "success": test_result["success"],
                "error": test_result.get("error"),
                "initialized": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

# Create global instance
sms_service = SMSService()