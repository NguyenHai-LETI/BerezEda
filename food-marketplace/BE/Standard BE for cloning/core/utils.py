"""
Core utility functions used across the application.
"""

import math
from datetime import date, datetime, timezone
from typing import Optional


def get_current_time() -> datetime:
    """
    Get current time in UTC as timezone-naive datetime.

    This function provides a consistent way to get the current time
    across the entire application, ensuring all timestamps are in UTC.

    Returns:
        datetime: Current UTC time without timezone info
    """
    return datetime.utcnow()


def get_current_time_utc() -> datetime:
    """
    Get current time in UTC as timezone-aware datetime.

    This function provides timezone-aware UTC datetime for use cases
    that require timezone information (e.g., analytics, comparisons).

    Returns:
        datetime: Current UTC time with timezone info
    """
    return datetime.now(timezone.utc)


def format_time_remaining(seconds: float) -> str:
    """
    Format remaining time in a human-readable format.

    Args:
        seconds: Number of seconds remaining

    Returns:
        str: Human-readable time format (e.g., "5 minutes 30 seconds")
    """
    if seconds <= 0:
        return "0 seconds"

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if secs > 0 or not parts:  # Show seconds if no other parts or if there are seconds
        parts.append(f"{secs} second{'s' if secs != 1 else ''}")

    return " ".join(parts)


def time_until(target_time: datetime, from_time: Optional[datetime] = None) -> float:
    """
    Calculate seconds until a target time.

    Args:
        target_time: The target datetime
        from_time: Starting time (defaults to current time)

    Returns:
        float: Seconds until target time (negative if target is in the past)
    """
    if from_time is None:
        from_time = get_current_time()

    delta = target_time - from_time
    return delta.total_seconds()


def is_time_expired(
    expiry_time: datetime, current_time: Optional[datetime] = None
) -> bool:
    """
    Check if a given time has expired.

    Args:
        expiry_time: Time to check for expiration
        current_time: Current time to compare against (defaults to now)

    Returns:
        bool: True if expired, False otherwise
    """
    if current_time is None:
        current_time = get_current_time()

    return current_time > expiry_time


def parse_position_string(position_str: str):
    if not position_str:
        return None

    # TODO: Make sure position string has valid format
    parts = position_str.strip().split(",")
    latitude = float(parts[0].strip())
    longitude = float(parts[1].strip())
    coords = [latitude, longitude]
    position = {"type": "Point", "coordinates": coords}
    return position


def get_distance(user_position: str, locker_position: str) -> float:
    """
    Calculate distance between user and locker using Haversine formula.

    Args:
        user_position: String in format "35.694003,139.982047" (latitude,longitude)
        locker_position: String in format "35.694003,139.982047" (latitude,longitude)

    Returns:
        Distance in kilometers (float)

    Raises:
        ValueError: If either position string is invalid

    Example:
        user_pos = "35.694003,139.982047"
        locker_pos = "35.695003,139.983047"
        distance = get_distance(user_pos, locker_pos)
        # Returns: 0.15 (km approximately)
    """

    user_point = parse_position_string(user_position)
    locker_point = parse_position_string(locker_position)

    user_coords = user_point["coordinates"]
    locker_coords = locker_point["coordinates"]

    # Degrees to radians
    lat1 = math.radians(user_coords[0])
    lon1 = math.radians(user_coords[1])
    lat2 = math.radians(locker_coords[0])
    lon2 = math.radians(locker_coords[1])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    earth_radius_km = 6371.0
    distance = earth_radius_km * c

    return round(distance, 3)


def parse_date_string(date_string: str) -> Optional[date]:
    """
    Parse a date string in YYYY-MM-DD format to a date object.

    Args:
        date_string: Date string in YYYY-MM-DD format

    Returns:
        date: Parsed date object or None if invalid format

    Example:
        >>> parse_date_string("2025-10-03")
        datetime.date(2025, 10, 3)

        >>> parse_date_string("invalid-date")
        None
    """
    try:
        return datetime.strptime(date_string, "%Y-%m-%d").date()
    except ValueError:
        return None


def format_datetime_for_firebase(dt: Optional[datetime]) -> Optional[str]:
    """
    Format datetime for Firebase storage without automatic timezone conversion.

    Args:
        dt: Datetime to format

    Returns:
        str: Formatted datetime string or None
    """
    if dt is None:
        return None

    # If datetime is timezone-aware, convert to UTC first
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
        # Remove timezone info to prevent Firebase from adding offset
        dt = dt.replace(tzinfo=None)

    return dt.isoformat()
