"""
Admin authentication middleware
"""
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.shared.auth import auth_service

security = HTTPBearer()

def verify_admin_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify admin JWT token"""
    token = credentials.credentials
    payload = auth_service.decode_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Check if user is admin (you'll need to add admin field to users table)
    user_id = payload.get("sub")
    # TODO: Check if user_id has admin privileges
    
    return user_id