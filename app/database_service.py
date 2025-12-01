# app/database_service.py - UPDATED
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
from app.models import UserInDB
from app.auth_service import AuthService
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self, supabase_client, auth_service: AuthService):
        self.supabase = supabase_client
        self.auth_service = auth_service
    
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