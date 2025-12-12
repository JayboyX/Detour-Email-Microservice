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

# Add this to app/advances/schemas.py
class AdvanceSummaryResponse(BaseModel):
    total_advanced: float = Field(default=0.0)
    total_repaid: float = Field(default=0.0)
    total_outstanding: float = Field(default=0.0)
    advances_count: int = Field(default=0)
    repaid_advances_count: int = Field(default=0)
    active_advances_count: int = Field(default=0)