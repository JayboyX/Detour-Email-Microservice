from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional, Dict
from app.auth.schemas import SuccessResponse

class TransactionBase(BaseModel):
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = None
    reference: Optional[str] = None
    metadata: Optional[Dict] = None

class PaymentRequest(TransactionBase):
    user_id: str
    payment_type: str  # e.g. "subscription", "bundle", "airtime", "advance_repayment"

class CreditRequest(TransactionBase):
    user_id: str
    credit_type: str  # e.g. "advance_credit"

class TransferRequest(BaseModel):
    from_user_id: str
    to_user_id: str
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = None
