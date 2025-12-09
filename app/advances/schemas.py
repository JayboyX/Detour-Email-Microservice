from pydantic import BaseModel, Field
from decimal import Decimal
from app.auth.schemas import SuccessResponse


class AdvanceRequest(BaseModel):
    """
    Request to TAKE an advance automatically.
    """
    user_id: str
    amount: Decimal = Field(..., gt=0)


class AutoRepayRun(BaseModel):
    """
    Placeholder for triggering auto-repay via cron.
    """
    pass
