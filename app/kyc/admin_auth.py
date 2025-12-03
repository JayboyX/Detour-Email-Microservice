"""
Admin authentication middleware
"""
from fastapi import HTTPException, Header
from typing import Optional
from app.shared.auth import auth_service
from app.shared.database import database_service

def verify_admin_token(admin_token: Optional[str] = Header(None, alias="admin-token")):
    """Verify admin JWT token from admin-token header"""
    if not admin_token:
        raise HTTPException(status_code=401, detail="Missing admin token")
    
    payload = auth_service.decode_token(admin_token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    admin_id = payload.get("sub")  # This should be the admin's user_id
    
    if not admin_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    # Check if user exists in admins table
    try:
        endpoint = f"/rest/v1/admins?user_id=eq.{admin_id}"
        response = database_service.supabase.make_request(
            "GET", endpoint, headers=database_service.supabase.service_headers
        )
        
        if not response:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Check if admin is active
        admin_data = response[0]
        if not admin_data.get('is_active', True):
            raise HTTPException(status_code=403, detail="Admin account is inactive")
        
        return admin_id
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"Admin verification failed: {str(e)}")