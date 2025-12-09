from fastapi import APIRouter
from app.advances.schemas import AdvanceRequest, AutoRepayRun
from app.advances.service import advances_service
from app.auth.schemas import SuccessResponse

router = APIRouter(tags=["advances"], prefix="/api/advances")


# -----------------------------------------------------------
# CHECK AVAILABLE ADVANCE FOR THE USER
# -----------------------------------------------------------
@router.get("/available/{user_id}", response_model=SuccessResponse)
async def get_available_advance(user_id: str):
    """Returns weekly_limit, used, performance_limit, and total available."""

    result = advances_service.get_available_advance(user_id)

    return SuccessResponse(
        success=True,
        message="Advance availability retrieved",
        data=result
    )


# -----------------------------------------------------------
# FULLY AUTOMATIC ADVANCE — TAKE ADVANCE
# -----------------------------------------------------------
@router.post("/take", response_model=SuccessResponse)
async def take_advance(req: AdvanceRequest):
    """Automatically validates and issues an advance (no approval needed)."""
    result = advances_service.take_advance(req)
    return SuccessResponse(**result)


# -----------------------------------------------------------
# AUTO REPAYMENT (cronjob)
# -----------------------------------------------------------
@router.post("/auto-repay", response_model=SuccessResponse)
async def auto_repay():
    """Runs weekly automatic repayment for all active advances."""
    result = advances_service.auto_repay()
    return SuccessResponse(**result)
