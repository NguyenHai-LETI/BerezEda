"""
Galilei Integration Service

Provides secure and clean interface for Galilei API operations
"""

import logging
from typing import Any, Dict, Optional

from .constants import (
    GalileiConfigError,
    get_auth_json,
    get_galilei_config,
    validate_galilei_config,
)

logger = logging.getLogger(__name__)


class GalileiService:
    """Main service class for Galilei integration"""

    def __init__(self):
        self._config: Optional[Dict[str, Any]] = None
        self._auth_json: Optional[Dict[str, Any]] = None

    @property
    def config(self) -> Dict[str, Any]:
        """Get validated configuration (cached)"""
        if self._config is None:
            self._config = get_galilei_config()
            validate_galilei_config(self._config)
        return self._config

    @property
    def auth_json(self) -> Dict[str, Any]:
        """Get authentication JSON (cached)"""
        if self._auth_json is None:
            self._auth_json = get_auth_json()
        return self._auth_json

    @property
    def api_id_locker(self) -> str:
        """Get API ID for locker"""
        return self.config["api_status_id"]

    def is_configured(self) -> bool:
        """Check if Galilei is properly configured"""
        try:
            validate_galilei_config(get_galilei_config())
            return True
        except GalileiConfigError:
            return False

    def get_locker_detail_url(
        self, full_unit_number: str, from_date: str, to_date: str
    ) -> str:
        """Generate locker detail API URL with date parameters"""
        base_url = (
            f"https://{self.api_id_locker}.execute-api.ap-northeast-1.amazonaws.com"
        )
        return f"{base_url}/locker/data?lockerid={full_unit_number}&from={from_date}&to={to_date}"

    def get_auth_url(self) -> str:
        """Get authentication URL"""
        return "https://cognito-idp.ap-northeast-1.amazonaws.com/"

    def get_changes_access_code_url(self) -> str:
        """Get URL for changing access code"""
        return "https://c33e0doh87.execute-api.ap-northeast-1.amazonaws.com/change_pin/locker"


# Global service instance
galilei_service = GalileiService()
