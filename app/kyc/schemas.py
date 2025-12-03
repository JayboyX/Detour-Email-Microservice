"""
Pydantic schemas for KYC
"""
from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import date, datetime
from enum import Enum

class KYCStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"

class BAVStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"

# KYC Submission
class KYCSubmitRequest(BaseModel):
    id_number: str
    first_name: str
    last_name: str
    date_of_birth: date
    phone_number: str
    address: str
    bank_account_number: str
    bank_name: str
    proof_of_address_url: Optional[str] = None
    id_document_url: Optional[str] = None
    selfie_url: Optional[str] = None

# KYC Update (Admin)
class KYCUpdateRequest(BaseModel):
    kyc_status: Optional[KYCStatus] = None
    bav_status: Optional[BAVStatus] = None
    notes: Optional[str] = None

# KYC Response
class KYCResponse(BaseModel):
    id: str
    user_id: str
    first_name: str
    last_name: str
    id_number: str
    phone_number: str
    kyc_status: str
    bav_status: str
    created_at: datetime
    updated_at: datetime

# Admin KYC List
class KYCListResponse(BaseModel):
    total: int
    pending: int
    verified: int
    rejected: int
    kycs: List[KYCResponse]

# Admin verification
class KYCVerifyRequest(BaseModel):
    kyc_id: str
    kyc_status: KYCStatus
    bav_status: BAVStatus
    admin_notes: Optional[str] = None