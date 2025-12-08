"""
Subscription Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, List


# ---------------------------------------------------------
# Admin: Create Package
# ---------------------------------------------------------
class CreatePackageRequest(BaseModel):
    name: str
    price: float
    period: str = "Weekly for 12 Months"
    description: Optional[str] = None
    benefits: List[str] = Field(default_factory=list)
    weekly_advance_limit: float = 0.0
    advance_percentage: int = 0
    auto_repay_rate: int = 20


# ---------------------------------------------------------
# User: Activate Subscription (NO PAYMENT)
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
# User: Upgrade / Downgrade Subscription
# ---------------------------------------------------------
class SubscriptionUpdateRequest(BaseModel):
    user_id: str
    package_id: str


# ---------------------------------------------------------
# Generic Response Model
# ---------------------------------------------------------
class SubscriptionResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
