from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional
from app.auth.schemas import SuccessResponse

class AirtimePurchaseRequest(BaseModel):
    user_id: str
    beneficiary_number: str
    network: str
    amount: Decimal = Field(..., gt=0)

class BundlePurchaseRequest(BaseModel):
    user_id: str
    beneficiary_number: str
    bundle_id: str  # From bundle_catalog
