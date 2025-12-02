"""
SMS Service using WinSMS API - FIXED VERSION
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
    """WinSMS service for sending OTP SMS messages - FIXED"""
    
    def __init__(self):
        self.sms_user = os.getenv('SMS_USER', settings.sms_user)
        self.sms_password = os.getenv('SMS_PASSWORD', settings.sms_password)
        self.api_url = settings.sms_api_url
        
        logger.info(f"SMSService initialized with user: {self.sms_user}")
        
        # Check if credentials are set
        if not self.sms_user or not self.sms_password:
            logger.warning("SMS credentials not configured. SMS sending will be simulated.")
            self.initialized = False
        else:
            self.initialized = True
            logger.info("✅ SMS Service ready for production")
    
    def send_otp_sms(self, phone_number: str, otp_code: str, user_name: str = "User") -> Dict[str, Any]:
        """
        Send OTP SMS via WinSMS API - FIXED
        """
        try:
            # Clean phone number
            cleaned_number = self._clean_phone_number(phone_number)
            
            if not self._validate_phone_number(cleaned_number):
                logger.error(f"Invalid phone number: {phone_number}")
                return {
                    "success": False,
                    "error": "Invalid phone number format",
                    "simulated": True
                }
            
            # Create SMS message
            message = f"Your Detour verification code is: {otp_code}. Valid for {settings.otp_expiry_minutes} minutes."
            
            # Always try to send via API if credentials exist
            if self.initialized and not settings.debug:
                result = self._send_via_winsms(cleaned_number, message)
                if result["success"]:
                    logger.info(f"✅ Real SMS sent to {cleaned_number}")
                    return result
                else:
                    logger.warning(f"SMS API failed, falling back to debug: {result.get('error')}")
                    # Fall through to debug mode
            
            # Fallback to debug/logging mode
            return self._debug_send(cleaned_number, otp_code, message)
            
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return self._debug_send(phone_number, otp_code, f"Error: {str(e)}")
    
    def _clean_phone_number(self, phone_number: str) -> str:
        """Clean and format phone number for WinSMS"""
        # Remove all non-digit characters
        digits = ''.join(filter(str.isdigit, phone_number))
        
        # Handle South African numbers
        if digits.startswith('27'):
            # Already in international format
            return digits
        elif digits.startswith('0'):
            # Convert local to international
            return '27' + digits[1:]
        else:
            # Assume it's already in some international format
            return digits
    
    def _validate_phone_number(self, phone_number: str) -> bool:
        """Validate phone number format"""
        # Remove all non-digits for validation
        digits = ''.join(filter(str.isdigit, phone_number))
        
        # South African numbers should be 11 digits (27 + 9 digits)
        return len(digits) == 11 and digits.startswith('27')
    
    def _send_via_winsms(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send SMS via WinSMS API - FIXED"""
        try:
            # Prepare query parameters exactly as WinSMS expects
            params = {
                "User": self.sms_user,  # Note: Capital U
                "Password": self.sms_password,  # Note: Capital P
                "Message": message,
                "Numbers": phone_number
            }
            
            # Build URL
            base_url = self.api_url.rstrip('/')
            query_string = urllib.parse.urlencode(params)
            url = f"{base_url}?{query_string}"
            
            logger.info(f"Sending SMS to WinSMS API: {url}")
            
            # Make request with timeout
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url)
                response_text = response.text.strip()
                
                logger.info(f"WinSMS Response: {response_text}")
                
                # Parse WinSMS response
                if "=" in response_text:
                    parts = response_text.split("=", 1)
                    if len(parts) == 2:
                        _, result = parts
                        result = result.replace("&", "").strip()
                        
                        # Check for errors
                        error_messages = {
                            "INSUFFICIENT CREDITS": "SMS credits are insufficient",
                            "ACCOUNTLOCKED": "SMS account is locked",
                            "BADDEST": "Invalid phone number",
                            "INVALIDUSER": "Invalid user credentials",
                            "INVALIDPASSWORD": "Invalid password",
                            "NOCREDIT": "No credit available"
                        }
                        
                        if result in error_messages:
                            return {
                                "success": False,
                                "error": error_messages[result],
                                "simulated": False
                            }
                        else:
                            # Success - WinSMS returns message ID
                            return {
                                "success": True,
                                "message_id": result,
                                "simulated": False,
                                "phone_number": phone_number
                            }
                
                # Unexpected response format
                return {
                    "success": False,
                    "error": f"Unexpected API response: {response_text}",
                    "simulated": False
                }
                
        except httpx.RequestError as e:
            logger.error(f"Network error sending SMS: {e}")
            return {
                "success": False,
                "error": f"Network error: {str(e)}",
                "simulated": False
            }
        except Exception as e:
            logger.error(f"Unexpected error sending SMS: {e}")
            return {
                "success": False,
                "error": f"SMS sending failed: {str(e)}",
                "simulated": False
            }
    
    def _debug_send(self, phone_number: str, otp_code: str, message: str) -> Dict[str, Any]:
        """Debug mode - log instead of sending"""
        debug_info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "DEBUG" if settings.debug else "FALLBACK",
            "phone_number": phone_number,
            "otp_code": otp_code,
            "message": message,
            "simulated": True
        }
        
        # Log to console
        print(f"\n{'='*60}")
        print(f"📱 {'DEBUG' if settings.debug else 'FALLBACK'} SMS")
        print(f"   To: {phone_number}")
        print(f"   OTP: {otp_code}")
        print(f"   Message: {message}")
        if not self.initialized:
            print(f"   ⚠️  SMS credentials not configured")
        print(f"{'='*60}\n")
        
        # Log to file
        try:
            import json
            with open('sms_debug.log', 'a', encoding='utf-8') as f:
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
    
    def test_connection(self) -> Dict[str, Any]:
        """Test SMS connection and credentials"""
        try:
            if not self.initialized:
                return {
                    "success": False,
                    "error": "SMS credentials not configured",
                    "initialized": False
                }
            
            # Try to send a test SMS to verify credentials
            test_result = self._send_via_winsms("27721234567", "Test SMS from Detour API")
            
            return {
                "success": test_result["success"],
                "error": test_result.get("error"),
                "initialized": True,
                "user": self.sms_user
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "initialized": self.initialized
            }


# Create global instance
sms_service = SMSService()