"""
Subscription Utility Helpers
"""

from datetime import datetime, timedelta
import uuid


# ---------------------------------------------------------
# Generate ISO timestamp (UTC)
# ---------------------------------------------------------
def now_iso() -> str:
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------
# Generate a new UUID string
# ---------------------------------------------------------
def new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------
# Next Friday Date
# ---------------------------------------------------------
def get_next_friday(from_date: datetime = None):
    if from_date is None:
        from_date = datetime.utcnow()

    # Monday = 0 ... Sunday = 6
    # Friday = 4
    days_ahead = 4 - from_date.weekday()
    if days_ahead <= 0:
        days_ahead += 7

    return (from_date + timedelta(days=days_ahead)).date()


# ---------------------------------------------------------
# Today's Midnight (UTC)
# ---------------------------------------------------------
def today_midnight():
    now = datetime.utcnow()
    return datetime(now.year, now.month, now.day)
