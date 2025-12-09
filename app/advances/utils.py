from datetime import datetime
from dateutil import parser


def now_iso():
    """Return a UTC ISO timestamp."""
    return datetime.utcnow().isoformat()


def weeks_since(created_at: str):
    """
    Calculate whole weeks since an advance was created.
    Used to track expected repayment timeline.
    """
    created = parser.parse(created_at)
    now = datetime.utcnow()
    diff_days = (now - created).days
    return diff_days // 7  # integer number of weeks


def calculate_repay_amount(wallet_balance: float, outstanding: float, rate: float):
    """
    Repay rule for auto-repay cycles:
    repay = min(wallet_balance * (rate / 100), outstanding)
    """
    repay = wallet_balance * (rate / 100)
    return min(repay, outstanding)
