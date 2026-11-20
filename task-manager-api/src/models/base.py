from datetime import datetime, timezone


def utcnow():
    """UTC sem tzinfo, no mesmo formato das datas já gravadas no banco."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
