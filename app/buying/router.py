from fastapi import APIRouter
from app.buying.schemas import AirtimePurchaseRequest, BundlePurchaseRequest
from app.buying.service import buying_service
from app.auth.schemas import SuccessResponse

router = APIRouter(tags=["buying"])

# -------------------------
# BUY AIRTIME
# -------------------------
@router.post("/airtime", response_model=SuccessResponse)
async def buy_airtime(req: AirtimePurchaseRequest):
    result = buying_service.buy_airtime(req)
    return SuccessResponse(**result)

# -------------------------
# BUY DATA or VOICE BUNDLE
# -------------------------
@router.post("/bundle", response_model=SuccessResponse)
async def buy_bundle(req: BundlePurchaseRequest):
    result = buying_service.buy_bundle(req)
    return SuccessResponse(**result)
