"""
Subscription Utility Helpers
"""

from datetime import datetime, timedelta


# ---------------------------------------------------------
# Next Friday Date
# ---------------------------------------------------------
def get_next_friday(from_date: datetime = None):
    if from_date is None:
        from_date = datetime.utcnow()

    days_ahead = 4 - from_date.weekday()
    if days_ahead <= 0:
        days_ahead += 7

    return (from_date + timedelta(days=days_ahead)).date()


# ---------------------------------------------------------
# Today Midnight
# ---------------------------------------------------------
def today_midnight():
    now = datetime.utcnow()
    return datetime(now.year, now.month, now.day)
