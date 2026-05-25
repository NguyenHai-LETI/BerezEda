"""
Galilei Integration Package

Provides secure integration with Galilei locker management system.

Usage:
    from apps.integrations.galilei import galilei_service

    # Check if configured
    if galilei_service.is_configured():
        # Get authentication data
        auth = galilei_service.auth_json

        # Get API URLs
        url = galilei_service.get_locker_detail_url("2023-01-01", "2023-01-31")
"""

from .constants import GalileiConfigError
from .service import galilei_service

__all__ = ["galilei_service", "GalileiConfigError"]
