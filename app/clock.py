from datetime import datetime, timezone


def utcnow():
    """Naive UTC for compatibility with the original database's DateTime columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
