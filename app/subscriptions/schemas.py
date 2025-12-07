"""
Subscription Schemas
"""

from pydantic import BaseModel
from typing import Optional, List


# ---------------------------------------------------------
# Admin: Create Package
# ---------------------------------------------------------
class CreatePackageRequest(BaseModel):
    name: str
    price: float
    period: str = "Weekly for 12 Months"
    description: Optional[str] = None
    benefits: Optional[List[str]] = []
    weekly_advance_limit: float = 0.0
    advance_percentage: int = 0
    auto_repay_rate: int = 20


# ---------------------------------------------------------
# User: Activate Subscription
# ---------------------------------------------------------
class ActivateSubscriptionRequest(BaseModel):
    user_id: str
    package_id: str


# ---------------------------------------------------------
# User: Cancel Subscription
# ---------------------------------------------------------
class CancelSubscriptionRequest(BaseModel):
    user_id: str
    reason: Optional[str] = None


# ---------------------------------------------------------
# Generic Response
# ---------------------------------------------------------
class SubscriptionResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
