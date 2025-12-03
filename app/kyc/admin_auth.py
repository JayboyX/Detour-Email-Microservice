"""
Admin authentication middleware
"""
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.shared.auth import auth_service
from app.shared.database import database_service

security = HTTPBearer()

def verify_admin_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify admin JWT token"""
    token = credentials.credentials
    payload = auth_service.decode_token(token)
    
    if not payload:
        raise HTTPException(401, "Invalid token")
    
    user_id = payload.get("sub")
    
    # Check if user exists in admin table
    try:
        endpoint = f"/rest/v1/admins?user_id=eq.{user_id}"
        response = database_service.supabase.make_request(
            "GET", endpoint, headers=database_service.supabase.service_headers
        )
        
        if not response:
            raise HTTPException(403, "Admin access required")
        
        return user_id
    except Exception as e:
        raise HTTPException(403, "Admin verification failed")