from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return current UTC time as a naive datetime (no tzinfo).
    Single source of truth for timestamps across the project.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Alias for backward compatibility
get_current_time = utcnow
