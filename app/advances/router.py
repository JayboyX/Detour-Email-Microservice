from fastapi import APIRouter
from app.advances.schemas import AdvanceRequest
from app.advances.service import advances_service
from app.auth.schemas import SuccessResponse

router = APIRouter(tags=["advances"])

# -----------------------------------------------------------
# CHECK AVAILABLE ADVANCE FOR THE USER
# -----------------------------------------------------------
@router.get("/available/{user_id}", response_model=SuccessResponse)
async def get_available_advance(user_id: str):
    """
    Retrieves the user's advance status:
    - weekly_limit: Max amount user can borrow per cycle
    - outstanding: Current unpaid advance
    - available: Borrowable amount (0 if any outstanding exists)
    - pool_limit: Issuer pool balance constraint
    """
    result = advances_service.get_available_advance(user_id)

    return SuccessResponse(
        success=True,
        message="Advance availability retrieved",
        data=result
    )


# -----------------------------------------------------------
# TAKE ADVANCE — FULLY AUTOMATIC (1-step)
# -----------------------------------------------------------
@router.post("/take", response_model=SuccessResponse)
async def take_advance(req: AdvanceRequest):
    """
    Issues an advance automatically:
    - Validates no outstanding advance exists
    - Checks weekly limit
    - Checks issuer pool liquidity
    - Credits user's wallet
    - Deducts from issuer pool
    - Creates advance record
    """
    result = advances_service.take_advance(req)
    return SuccessResponse(**result)


# -----------------------------------------------------------
# AUTO-REPAYMENT (WEEKLY CRONJOB)
# -----------------------------------------------------------
@router.post("/auto-repay", response_model=SuccessResponse)
async def auto_repay():
    """
    Executes weekly repayment cycle:
    - weekly_repay = total_amount * repay_rate%
    - Deducts repayment from wallet (if funds available)
    - Updates outstanding balance
    - Returns funds to issuer pool
    - Marks advance fully repaid when balance reaches 0
    """
    result = advances_service.auto_repay()
    return SuccessResponse(**result)
