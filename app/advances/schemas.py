from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional
from app.auth.schemas import SuccessResponse

class AdvanceRequest(BaseModel):
    user_id: str
    amount: Decimal = Field(..., gt=0)

class ApproveAdvanceRequest(BaseModel):
    user_id: str
    amount: Decimal
    issuer_pool_id: str

class ManualRepaymentRequest(BaseModel):
    user_id: str
    amount: Decimal

class AutoRepayRun(BaseModel):
    pass
