import uuid
from datetime import datetime

def generate_reference(prefix="TX"):
    return f"{prefix}-{str(uuid.uuid4())[:8].upper()}"

def now_iso():
    return datetime.utcnow().isoformat()
