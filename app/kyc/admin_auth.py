"""
Admin Authentication Middleware
"""

import logging
from fastapi import HTTPException, Header
from typing import Optional

from app.shared.auth import auth_service
from app.shared.database import database_service

logger = logging.getLogger(__name__)


def verify_admin_token(admin_token: Optional[str] = Header(None, alias="admin-token")):
    """Validate admin JWT and ensure admin exists"""
    if not admin_token:
        raise HTTPException(status_code=401, detail="Missing admin token")

    payload = auth_service.decode_token(admin_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    admin_id = payload.get("sub")
    if not admin_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    try:
        endpoint = f"/rest/v1/admins?id=eq.{admin_id}"
        response = database_service.supabase.make_request(
            "GET", endpoint, headers=database_service.supabase.service_headers
        )
        if not response:
            raise HTTPException(status_code=403, detail="Admin access required")

        admin = response[0]
        if not admin.get("is_active", True):
            raise HTTPException(status_code=403, detail="Admin account inactive")

        return admin_id

    except Exception as e:
        logger.error(f"Admin verification failed ({admin_id}): {e}")
        raise HTTPException(status_code=403, detail="Admin verification failed")
