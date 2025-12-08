"""
Subscription Router
"""

from fastapi import APIRouter
from app.subscriptions.schemas import (
    CreatePackageRequest,
    ActivateSubscriptionRequest,
    CancelSubscriptionRequest,
    SubscriptionUpdateRequest,
)
from app.subscriptions.service import subscription_service
from app.advances.service import advances_service
from app.auth.schemas import SuccessResponse
from app.shared.database import database_service

router = APIRouter(tags=["subscriptions"])


# ---------------------------------------------------------
# Admin: Create Subscription Package
# ---------------------------------------------------------
@router.post("/package/create", response_model=SuccessResponse)
async def create_package(req: CreatePackageRequest):
    result = subscription_service.create_package(req)
    return SuccessResponse(**result)


# ---------------------------------------------------------
# User: Get All Active Packages
# ---------------------------------------------------------
@router.get("/packages", response_model=SuccessResponse)
async def get_all_packages():
    packages = database_service.supabase.make_request(
        method="GET",
        endpoint="/rest/v1/subscription_packages?is_active=eq.true&order=price.asc",
        headers=database_service.supabase.anon_headers,
    )
    return SuccessResponse(
        success=True,
        message="Subscription packages retrieved",
        data={"packages": packages},
    )


# ---------------------------------------------------------
# User: Get Active Subscription
# ---------------------------------------------------------
@router.get("/user/{user_id}", response_model=SuccessResponse)
async def get_user_subscription(user_id: str):
    sub = subscription_service.get_active_subscription(user_id)
    return SuccessResponse(
        success=True,
        message="User subscription retrieved",
        data=sub,
    )


# ---------------------------------------------------------
# User: Activate Subscription (NO PAYMENT)
# ---------------------------------------------------------
@router.post("/activate", response_model=SuccessResponse)
async def activate_subscription(req: ActivateSubscriptionRequest):
    result = subscription_service.activate_subscription(req.user_id, req.package_id)
    return SuccessResponse(**result)


# ---------------------------------------------------------
# User: Upgrade Subscription
# ---------------------------------------------------------
@router.post("/upgrade", response_model=SuccessResponse)
async def upgrade_subscription(req: SubscriptionUpdateRequest):
    result = subscription_service.upgrade_subscription(req.user_id, req.package_id)
    return SuccessResponse(**result)


# ---------------------------------------------------------
# User: Downgrade Subscription
# ---------------------------------------------------------
@router.post("/downgrade", response_model=SuccessResponse)
async def downgrade_subscription(req: SubscriptionUpdateRequest):
    result = subscription_service.downgrade_subscription(req.user_id, req.package_id)
    return SuccessResponse(**result)


# ---------------------------------------------------------
# User: Cancel Subscription
# ---------------------------------------------------------
@router.post("/cancel", response_model=SuccessResponse)
async def cancel_subscription(req: CancelSubscriptionRequest):
    result = subscription_service.cancel_subscription(req.user_id, req.reason)
    return SuccessResponse(**result)


# ---------------------------------------------------------
# User: Get Available Advance Limits
# ---------------------------------------------------------
@router.get("/limits/{user_id}", response_model=SuccessResponse)
async def get_user_limits(user_id: str):
    sub = subscription_service.get_active_subscription(user_id)
    if not sub:
        return SuccessResponse(success=False, message="No active subscription found")

    pkg = subscription_service.get_package(sub["package_id"])
    if not pkg:
        return SuccessResponse(success=False, message="Subscription package not found")

    weekly_limit = float(pkg["weekly_advance_limit"])

    outstanding = advances_service.get_outstanding(user_id)
    used = sum(float(x["outstanding_amount"]) for x in outstanding)
    remaining = max(weekly_limit - used, 0)

    return SuccessResponse(
        success=True,
        message="Advance limits retrieved",
        data={
            "weekly_limit": weekly_limit,
            "used": used,
            "available": remaining,
            "outstanding_count": len(outstanding),
            "subscription_package": pkg,
        },
    )


# ---------------------------------------------------------
# Cron: Weekly Billing
# ---------------------------------------------------------
@router.get("/cron/bill", response_model=SuccessResponse)
async def run_weekly_billing():
    results = subscription_service.bill_all_users()
    return SuccessResponse(
        success=True,
        message="Weekly billing executed",
        data={"results": results},
    )
