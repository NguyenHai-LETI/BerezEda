"""
Order Utility Functions

Common utility functions used across the orders module.
"""

import secrets
import string
from typing import Optional

from apps.core.utils import get_current_time


def generate_order_number() -> str:
    """
    Generate a unique order number.

    Format: ORD{timestamp}{random_suffix}
    Example: ORD202501201234561234
    """
    timestamp = get_current_time().strftime("%Y%m%d%H%M%S")
    random_suffix = "".join(secrets.choice(string.digits) for _ in range(4))
    return f"ORD{timestamp}{random_suffix}"


def generate_pickup_code() -> str:
    """
    Generate a 6-digit pickup code.

    Returns a random 6-digit numeric string.
    """
    return "".join(secrets.choice(string.digits) for _ in range(6))


def sales_duration_to_minutes(sales_duration: Optional[str]) -> Optional[int]:
    """
    Convert human-readable sales_duration to minutes.

    Args:
        sales_duration: Japanese time format string
            Examples: '30分' (30 minutes), '1時間' (1 hour), '1時間30分' (1 hour 30 minutes)

    Returns:
        Total minutes as integer, or None if parsing fails

    Examples:
        >>> sales_duration_to_minutes('30分')
        30
        >>> sales_duration_to_minutes('1時間')
        60
        >>> sales_duration_to_minutes('1時間30分')
        90
    """
    if not sales_duration:
        return None

    try:
        # Normalize string
        s = sales_duration.replace(" ", "")
        minutes = 0

        # Handle forms like '30分'
        if "分" in s:
            # e.g. '30分' or '1時間30分'
            parts = s.split("時間")
            if len(parts) == 2:
                # parts[0] -> hours, parts[1] -> e.g. '30分'
                hours = int(parts[0]) if parts[0] else 0
                minutes_part = parts[1].replace("分", "")
                minutes = hours * 60 + (int(minutes_part) if minutes_part else 0)
            else:
                # pure minutes like '30分'
                minutes = int(s.replace("分", ""))
        elif "時間" in s:
            # e.g. '1時間'
            hours = int(s.replace("時間", ""))
            minutes = hours * 60
        else:
            return None

        return int(minutes)
    except Exception:
        return None
