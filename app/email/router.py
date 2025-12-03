"""
Email microservice router
"""
from fastapi import APIRouter, BackgroundTasks
from app.email.service import email_service
from app.shared.database import database_service
from app.shared.auth import auth_service
from app.config import settings
from datetime import datetime, timedelta, timezone

router = APIRouter(tags=["email"])

@router.get("/test-email")
async def test_email():
    """Test email service"""
    return {
        "success": True,
        "message": "Email service is running",
        "sender": email_service.sender_email,
        "has_ses_permissions": email_service.has_ses_permissions
    }

@router.get("/debug")
async def debug_email():
    """Debug email service"""
    return {
        "sender": email_service.sender_email,
        "has_ses_permissions": email_service.has_ses_permissions,
        "debug_mode": settings.debug
    }