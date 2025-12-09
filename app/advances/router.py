from fastapi import APIRouter
from app.advances.schemas import AdvanceRequest
from app.advances.service import advances_service
from app.auth.schemas import SuccessResponse

router = APIRouter(tags=["advances"], prefix="/api/advances")


# -----------------------------------------------------------
# CHECK AVAILABLE ADVANCE FOR THE USER
# -----------------------------------------------------------
@router.get("/available/{user_id}", response_model=SuccessResponse)
async def get_available_advance(user_id: str):
    """
    Returns:
    - weekly_limit
    - outstanding balance
    - available advance (0 if user still owes)
    - pool_limit
    """
    result = advances_service.get_available_advance(user_id)

    return SuccessResponse(
        success=True,
        message="Advance availability retrieved",
        data=result
    )


# -----------------------------------------------------------
# TAKE ADVANCE — FULLY AUTOMATIC
# -----------------------------------------------------------
@router.post("/take", response_model=SuccessResponse)
async def take_advance(req: AdvanceRequest):
    """
    Auto-issues an advance:
    - Validates no outstanding advance exists
    - Checks issuer pool liquidity
    - Credits wallet
    - Creates advance record
    - Deducts from issuer pool automatically
    """
    result = advances_service.take_advance(req)
    return SuccessResponse(**result)


# -----------------------------------------------------------
# AUTO REPAYMENT (WEEKLY CRONJOB)
# -----------------------------------------------------------
@router.post("/auto-repay", response_model=SuccessResponse)
async def auto_repay():
    """
    Runs weekly automatic repayment:
    - Calculates fixed weekly repayment = total_amount * repay_rate%
    - Ensures wallet has enough balance
    - Deducts repayment from wallet
    - Updates outstanding balance
    - Marks advance repaid when outstanding = 0
    - Returns repayment to issuer pool
    """
    result = advances_service.auto_repay()
    return SuccessResponse(**result)
