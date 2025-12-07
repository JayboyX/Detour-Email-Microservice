from datetime import datetime
from dateutil import parser

def now_iso():
    return datetime.utcnow().isoformat()

def weeks_since(created_at: str):
    """
    Calculate whole weeks since an advance was created.
    """
    created = parser.parse(created_at)
    now = datetime.utcnow()
    diff_days = (now - created).days
    return diff_days // 7  # integer weeks

def calculate_repay_amount(wallet_balance: float, outstanding: float, rate: float):
    """
    Old rule: repay = wallet_balance * rate%
    (Kept for compatibility)
    """
    repay = wallet_balance * (rate / 100)
    return min(repay, outstanding)
