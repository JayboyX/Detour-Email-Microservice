"""
SMS Router
"""

from fastapi import APIRouter
from app.sms.service import sms_service

router = APIRouter(tags=["sms"])


# ---------------------------------------------------------
# Health Check
# ---------------------------------------------------------
@router.get("/test-sms")
async def test_sms():
    result = sms_service.test_connection()
    return {
        "success": result["success"],
        "message": "SMS service test",
        "data": result
    }
