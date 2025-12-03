"""
SMS microservice router
"""
from fastapi import APIRouter, BackgroundTasks
from app.sms.service import sms_service
from app.sms.otp_service import otp_service

router = APIRouter(tags=["sms"])

@router.get("/test-sms")
async def test_sms():
    """Test SMS service"""
    result = sms_service.test_connection()
    return {
        "success": result["success"],
        "message": "SMS service test",
        "data": result
    }