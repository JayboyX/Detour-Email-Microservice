# app/database_service.py - UPDATED
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import uuid
from app import otp_service
from app.models import UserInDB
from app.auth_service import AuthService
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self, supabase_client, auth_service: AuthService):
        self.supabase = supabase_client
        self.auth_service = auth_service
    
    # We DO Email things here

    def create_user(self, user_data: Dict[str, Any]) -> Optional[UserInDB]:
        """Create a new user in Supabase"""
        try:
            # Hash the password
            hashed_password = self.auth_service.get_password_hash(user_data['password'])
            
            # Prepare user data for Supabase
            user_record = {
                'id': str(uuid.uuid4()),
                'full_name': user_data['full_name'],
                'email': user_data['email'].lower(),
                'password_hash': hashed_password,
                'terms_agreed': user_data['terms_agreed'],
                'email_verified': False,
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Add optional fields
            if 'phone_number' in user_data and user_data['phone_number']:
                user_record['phone_number'] = user_data['phone_number']
            
            # Insert into Supabase using service key (for write operations)
            response = self.supabase.insert_user(user_record, use_service_key=True)
            
            if response and isinstance(response, list) and len(response) > 0:
                return UserInDB.from_supabase(response[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Get user by email"""
        try:
            response = self.supabase.get_user_by_email(email, use_service_key=False)
            
            if response:
                return UserInDB.from_supabase(response)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """Get user by ID"""
        try:
            response = self.supabase.get_user_by_id(user_id, use_service_key=False)
            
            if response:
                return UserInDB.from_supabase(response)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user fields"""
        try:
            # Convert datetime to ISO format for Supabase
            processed_updates = {}
            for key, value in updates.items():
                if isinstance(value, datetime):
                    processed_updates[key] = value.isoformat()
                else:
                    processed_updates[key] = value
            
            response = self.supabase.update_user(user_id, processed_updates, use_service_key=True)
            
            # Check if update was successful
            return response is not None and len(response) > 0
            
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False
    
    def verify_email(self, user_id: str) -> bool:
        """Mark user's email as verified"""
        return self.update_user(user_id, {
            'email_verified': True,
            'verification_token': None,
            'token_expires_at': None
        })
    
    def set_verification_token(self, user_id: str, token: str, expires_at: datetime) -> bool:
        """Set verification token for user"""
        return self.update_user(user_id, {
            'verification_token': token,
            'token_expires_at': expires_at.isoformat()
        })
    
    def check_email_exists(self, email: str) -> bool:
        """Check if email already exists"""
        try:
            return self.supabase.check_email_exists(email, use_service_key=False)
            
        except Exception as e:
            logger.error(f"Error checking email existence: {e}")
            return False
        

    # We DO SMS things here
    
    def get_kyc_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get KYC information for user"""
        try:
            endpoint = f"/rest/v1/kyc_information?user_id=eq.{user_id}"
            headers = self.supabase.anon_headers
            response = self.supabase.make_request("GET", endpoint, headers=headers)
            
            if response and isinstance(response, list) and len(response) > 0:
                return response[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting KYC: {e}")
            return None
    
    def update_kyc_phone_verification(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update phone verification fields in KYC"""
        try:
            endpoint = f"/rest/v1/kyc_information?user_id=eq.{user_id}"
            headers = self.supabase.service_headers
            
            # Process datetime values
            processed_updates = {}
            for key, value in updates.items():
                if isinstance(value, datetime):
                    processed_updates[key] = value.isoformat()
                else:
                    processed_updates[key] = value
            
            response = self.supabase.make_request("PATCH", endpoint, processed_updates, headers)
            return response is not None and len(response) > 0
            
        except Exception as e:
            logger.error(f"Error updating KYC: {e}")
            return False
    
    def set_phone_otp(self, user_id: str, otp_code: str, expires_at: datetime) -> bool:
        """Set OTP for phone verification"""
        return self.update_kyc_phone_verification(user_id, {
            'phone_verification_otp': otp_code,
            'phone_otp_expires_at': expires_at.isoformat(),
            'phone_otp_last_sent': datetime.now(timezone.utc).isoformat(),
            'phone_otp_attempts': 0
        })
    
    def verify_phone_otp(self, user_id: str, otp_code: str) -> Dict[str, Any]:
        """Verify phone OTP - FIXED"""
        try:
            # Import otp_service here to avoid circular imports
            from app.otp_service import otp_service
            
            # Get current KYC info
            kyc_info = self.get_kyc_by_user_id(user_id)
            if not kyc_info:
                return {
                    "success": False, 
                    "error": "KYC information not found. Please complete KYC first.",
                    "user_id": user_id
                }
            
            # Check if already verified
            if kyc_info.get('phone_verified'):
                return {
                    "success": True, 
                    "already_verified": True,
                    "user_id": user_id
                }
            
            # Check attempts
            attempts = kyc_info.get('phone_otp_attempts', 0)
            if attempts >= settings.otp_max_attempts:
                return {
                    "success": False, 
                    "error": "Too many attempts. Please request a new OTP.",
                    "user_id": user_id
                }
            
            # Get stored OTP and expiry
            stored_otp = kyc_info.get('phone_verification_otp')
            stored_expiry = kyc_info.get('phone_otp_expires_at')
            
            if not stored_otp or not stored_expiry:
                return {
                    "success": False, 
                    "error": "No OTP found. Please request a new one.",
                    "user_id": user_id
                }
            
            # Verify OTP using otp_service
            if otp_service.is_otp_valid(stored_otp, stored_expiry, otp_code):
                # Mark phone as verified
                success = self.update_kyc_phone_verification(user_id, {
                    'phone_verified': True,
                    'phone_verification_otp': None,
                    'phone_otp_expires_at': None,
                    'phone_otp_attempts': 0
                })
                
                if success:
                    return {
                        "success": True, 
                        "verified": True,
                        "user_id": user_id
                    }
                else:
                    return {
                        "success": False, 
                        "error": "Failed to update verification status",
                        "user_id": user_id
                    }
            else:
                # Increment attempt counter
                self.update_kyc_phone_verification(user_id, {
                    'phone_otp_attempts': attempts + 1
                })
                
                remaining_attempts = settings.otp_max_attempts - (attempts + 1)
                error_msg = "Invalid OTP code"
                if remaining_attempts <= 0:
                    error_msg = "Too many failed attempts. Please request a new OTP."
                
                return {
                    "success": False, 
                    "error": error_msg,
                    "remaining_attempts": remaining_attempts,
                    "user_id": user_id
                }
                
        except Exception as e:
            logger.error(f"Error verifying OTP: {e}")
            return {
                "success": False, 
                "error": f"Verification failed: {str(e)}",
                "user_id": user_id
            }