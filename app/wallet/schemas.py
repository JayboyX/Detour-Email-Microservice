"""
Pydantic schemas for Wallet
"""
from pydantic import BaseModel, validator, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from decimal import Decimal

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

# Wallet Creation
class WalletCreateRequest(BaseModel):
    user_id: str = Field(..., min_length=1)

# Wallet Response
class WalletResponse(BaseModel):
    id: str
    user_id: str
    wallet_number: str
    balance: Decimal = Field(default=0.00)
    currency: str = Field(default="ZAR")
    status: WalletStatus = Field(default=WalletStatus.ACTIVE)
    created_at: datetime
    updated_at: datetime
    last_transaction_at: Optional[datetime] = None

# Transaction Request
class TransactionRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=255)
    reference: Optional[str] = Field(None, max_length=100)
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v

class DepositRequest(TransactionRequest):
    pass

class WithdrawalRequest(TransactionRequest):
    pass

# Transaction Response
class TransactionResponse(BaseModel):
    id: str
    wallet_id: str
    transaction_type: TransactionType
    amount: Decimal
    currency: str = Field(default="ZAR")
    reference: str
    description: Optional[str]
    status: TransactionStatus
    metadata: Optional[dict]
    created_at: datetime

# Wallet Balance
class BalanceResponse(BaseModel):
    wallet_id: str
    wallet_number: str
    balance: Decimal
    currency: str
    last_updated: datetime

# Transaction List
class TransactionListResponse(BaseModel):
    wallet_id: str
    total_transactions: int
    current_balance: Decimal
    transactions: List[TransactionResponse]

# Success Response (reuse from auth)
from app.auth.schemas import SuccessResponse