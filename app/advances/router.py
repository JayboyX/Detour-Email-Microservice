from fastapi import APIRouter
from app.advances.schemas import (
    AdvanceRequest,
    ApproveAdvanceRequest,
    ManualRepaymentRequest,
    AutoRepayRun
)
from app.advances.service import advances_service
from app.auth.schemas import SuccessResponse

router = APIRouter(tags=["advances"], prefix="/api/advances")


# -----------------------------------------------------------
# CHECK AVAILABLE ADVANCE FOR THE USER
# -----------------------------------------------------------
@router.get("/available/{user_id}", response_model=SuccessResponse)
async def get_available_advance(user_id: str):
    """Returns weekly_limit, used outstanding, and available."""
    
    # 1️⃣ Get subscription limits
    limits, error = advances_service.get_user_limits(user_id)
    if error:
        return SuccessResponse(
            success=False,
            message=error["message"],
            data={
                "weekly_limit": 0,
                "used": 0,
                "available": 0
            }
        )

    # Extract values safely
    weekly_limit = float(limits.get("weekly_limit", 0))

    # 2️⃣ Load outstanding safely
    outstanding = advances_service.get_outstanding(user_id) or []
    used = sum(float(x.get("outstanding_amount", 0)) for x in outstanding)

    available = max(0, weekly_limit - used)

    return SuccessResponse(
        success=True,
        message="Advance availability retrieved",
        data={
            "weekly_limit": weekly_limit,
            "used": used,
            "available": available,
        }
    )



# -----------------------------------------------------------
# REQUEST ADVANCE (eligibility check only)
# -----------------------------------------------------------
@router.post("/request", response_model=SuccessResponse)
async def request_advance(req: AdvanceRequest):
    result = advances_service.request_advance(req)
    return SuccessResponse(**result)


# -----------------------------------------------------------
# APPROVE ADVANCE (credit wallet + create record)
# -----------------------------------------------------------
@router.post("/approve", response_model=SuccessResponse)
async def approve_advance(req: ApproveAdvanceRequest):
    result = advances_service.approve_advance(req)
    return SuccessResponse(**result)


# -----------------------------------------------------------
# MANUAL REPAYMENT (optional)
# -----------------------------------------------------------
@router.post("/repay", response_model=SuccessResponse)
async def manual_repay(req: ManualRepaymentRequest):
    result = advances_service.manual_repay(req)
    return SuccessResponse(**result)


# -----------------------------------------------------------
# AUTO REPAYMENT (cronjob)
# -----------------------------------------------------------
@router.post("/auto-repay", response_model=SuccessResponse)
async def auto_repay():
    result = advances_service.auto_repay()
    return SuccessResponse(**result)
