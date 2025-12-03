"""
Auth service business logic
"""
from typing import Optional, Dict, Any
from datetime import datetime, timezone

class AuthService:
    """Business logic for authentication"""
    
    def __init__(self):
        from app.shared.database import database_service
        from app.shared.auth import auth_service as shared_auth_service
        self.db = database_service
        self.auth = shared_auth_service
    
    def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new user"""
        # Check if email exists
        if self.db.check_email_exists(user_data['email']):
            return {"success": False, "message": "Email already registered"}
        
        # Create user
        user = self.db.create_user(user_data)
        if not user:
            return {"success": False, "message": "Failed to create user"}
        
        return {"success": True, "user": user, "message": "User created"}
    
    def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user login"""
        user = self.db.get_user_by_email(email)
        if not user:
            return {"success": False, "message": "Invalid credentials"}
        
        if not self.auth.verify_password(password, user.get('password_hash', '')):
            return {"success": False, "message": "Invalid credentials"}
        
        if not user.get('email_verified'):
            return {
                "success": False,
                "message": "Email not verified",
                "requires_verification": True
            }
        
        # Generate access token
        access_token = self.auth.create_access_token(user['id'])
        
        return {
            "success": True,
            "access_token": access_token,
            "user": user
        }
    
    def verify_email_token(self, token: str) -> Dict[str, Any]:
        """Verify email verification token"""
        payload = self.auth.decode_token(token)
        if not payload or payload.get("purpose") != "email_verification":
            return {"success": False, "message": "Invalid token"}
        
        user_id = payload.get("sub")
        user = self.db.get_user_by_id(user_id)
        
        if not user:
            return {"success": False, "message": "User not found"}
        
        if user.get('email_verified'):
            return {"success": True, "already_verified": True, "user": user}
        
        # Verify the token matches
        if user.get('verification_token') != token:
            return {"success": False, "message": "Invalid verification token"}
        
        # Check expiry
        expires_at = user.get('token_expires_at')
        if expires_at:
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            if expires_at < datetime.now(timezone.utc):
                return {"success": False, "message": "Token expired"}
        
        # Mark email as verified
        success = self.db.verify_email(user_id)
        if success:
            return {"success": True, "verified": True, "user": user}
        else:
            return {"success": False, "message": "Failed to verify email"}

# Create instance
auth_service = AuthService()