"""
Wallet Schemas
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum
from datetime import datetime
from decimal import Decimal

from app.auth.schemas import SuccessResponse


class WalletStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    PAYMENT = "payment"
    REFUND = "refund"
    ACCOUNT_OPENING = "account_opening"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WalletCreateRequest(BaseModel):
    user_id: str = Field(..., min_length=1)


class WalletResponse(BaseModel):
    id: str
    user_id: str
    wallet_number: str
    balance: Decimal
    currency: str
    status: WalletStatus
    created_at: datetime
    updated_at: datetime
    last_transaction_at: Optional[datetime]


class TransactionRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = None
    reference: Optional[str] = None

    @validator("amount")
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


class DepositRequest(TransactionRequest):
    pass


class WithdrawalRequest(TransactionRequest):
    pass


class TransactionResponse(BaseModel):
    id: str
    wallet_id: str
    transaction_type: TransactionType
    amount: Decimal
    currency: str
    reference: str
    description: Optional[str]
    status: TransactionStatus
    metadata: Optional[dict]
    created_at: datetime


class TransactionListResponse(BaseModel):
    wallet_id: str
    total_transactions: int
    current_balance: Decimal
    transactions: List[TransactionResponse]
