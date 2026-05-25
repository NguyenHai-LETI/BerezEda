"""MynaPortal API client for handling government data requests."""

import json
import logging
import threading
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .config import (
    BACKEND_REDIRECT_URL,
    IF001_03_URL,
    IF001_04_URL,
    IF001_06_URL,
    INQUIRY_DATE,
    SERVICE_ID,
    SERVICE_PROVIDER_ID,
    TELEGRAM_TYPES,
)
from .exceptions import MynaRequestException, MynaResultException, MynaTokenException

# Thread-safe sequence counter for telegramId uniqueness within the same second
_telegram_seq_lock = threading.Lock()
_telegram_seq_last_second: str = ""
_telegram_seq_counter: int = 0


def _next_telegram_sequence(yymmddhhmmss: str) -> int:
    """Return a unique sequence number for the given datetime second."""
    global _telegram_seq_last_second, _telegram_seq_counter
    with _telegram_seq_lock:
        if yymmddhhmmss != _telegram_seq_last_second:
            _telegram_seq_last_second = yymmddhhmmss
            _telegram_seq_counter = 1
        else:
            _telegram_seq_counter += 1
        return _telegram_seq_counter

logger = logging.getLogger(__name__)


class MynaPortalApiClient:
    """Client for interacting with MynaPortal API services."""

    def __init__(self, code: str, state: str):
        """
        Initialize the API client.

        Args:
            code: Authorization code from OAuth flow
            state: State parameter for security
        """
        self.code = code
        self.state = state
        self.grant_type = "authorization_code"
        self.redirect_uri = BACKEND_REDIRECT_URL
        self.client_id = f"{SERVICE_PROVIDER_ID}_{SERVICE_ID}"

    def _log_api_call(
        self,
        method: str,
        url: str,
        headers: Dict[str, Any],
        data: Any,
        response: requests.Response,
    ):
        """Helper to log detailed API request and response information."""
        # Build curl command
        curl_parts = [f"curl -X {method}"]

        # Add headers
        for key, value in headers.items():
            # Escape single quotes in header values
            escaped_value = str(value).replace("'", "'\"'\"'")
            curl_parts.append(f"-H '{key}: {escaped_value}'")

        # Add data/body
        if data is not None:
            if isinstance(data, dict):
                # Check if Content-Type is form-urlencoded
                content_type = headers.get("Content-Type", "")
                if "application/x-www-form-urlencoded" in content_type:
                    # Form data - URL encode values
                    form_data = urlencode(data)
                    escaped_form = form_data.replace("'", "'\"'\"'")
                    curl_parts.append(f"-d '{escaped_form}'")
                else:
                    # JSON data
                    json_data = json.dumps(data, ensure_ascii=False)
                    escaped_json = json_data.replace("'", "'\"'\"'")
                    curl_parts.append(f"-d '{escaped_json}'")
            else:
                escaped_data = str(data).replace("'", "'\"'\"'")
                curl_parts.append(f"-d '{escaped_data}'")

        # Add URL
        curl_parts.append(f"'{url}'")
        curl_command = " \\\n  ".join(curl_parts)

        log_msg = (
            f"\n{'='*50}\n"
            f"MYNAPORTAL API CALL:\n"
            f"Method: {method}\n"
            f"URL: {url}\n"
            f"\nCURL COMMAND:\n{curl_command}\n"
            f"\nRequest Headers: {json.dumps(headers, indent=2, ensure_ascii=False)}\n"
            f"Request Body: {json.dumps(data, indent=2, ensure_ascii=False) if isinstance(data, (dict, list)) else data}\n"
            f"{'-'*20}\n"
            f"Response Status: {response.status_code}\n"
            f"Response Body: {response.text}\n"
            f"{'='*50}"
        )
        logger.info(log_msg)

    def get_access_token(self) -> Dict[str, Any]:
        """
        Get access token from authorization code.

        Returns:
            Token response dictionary

        Raises:
            MynaTokenException: If token acquisition fails
        """
        url = f"{IF001_03_URL}/oauth/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": self.grant_type,
            "code": self.code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
        }

        try:
            response = requests.post(url, headers=headers, data=data, timeout=30)
            self._log_api_call("POST", url, headers, data, response)

            if response.status_code in [200, 401]:
                return response.json()
            else:
                raise MynaTokenException(
                    f"Token request failed with status {response.status_code}: {response.text}"
                )

        except requests.exceptions.RequestException as e:
            raise MynaTokenException(f"Network error during token request: {e}")
        except Exception as e:
            raise MynaTokenException(f"Unexpected error during token request: {e}")

    def submit_data_request(
        self, token: str, telegram_id: str, date: str, mode: int = 1
    ) -> Dict[str, Any]:
        """
        Submit a data provision request.

        Args:
            token: Access token
            telegram_id: Unique telegram identifier
            date: Date for inquiry
            mode: Request mode (default: 1)

        Returns:
            Request response dictionary

        Raises:
            MynaRequestException: If request submission fails
        """
        url = f"{IF001_04_URL}/request"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        data = {
            "commonHeader": {
                "telegramId": telegram_id,
                "telegramType": TELEGRAM_TYPES["REQUEST"],
                "mode": str(mode),
                "processId": "",
                "errorCode": "",
            },
            "selfProvisionDataReqInfo": {"inquiryCondition": f"Date={date}"},
        }

        try:
            response = requests.post(
                url, data=json.dumps(data), headers=headers, timeout=30
            )
            self._log_api_call("POST", url, headers, data, response)

            if response.status_code == 200:
                return response.json()
            else:
                raise MynaRequestException(
                    f"Data request failed with status {response.status_code}: {response.text}"
                )

        except requests.exceptions.RequestException as e:
            raise MynaRequestException(f"Network error during data request: {e}")
        except Exception as e:
            raise MynaRequestException(f"Unexpected error during data request: {e}")

    def get_result(
        self, token: str, telegram_id: str, process_id: str, mode: int = 1
    ) -> Dict[str, Any]:
        """
        Get result of data provision request.

        Args:
            token: Access token
            telegram_id: Unique telegram identifier
            process_id: Process ID from request response
            mode: Request mode (default: 1)

        Returns:
            Result response dictionary

        Raises:
            MynaResultException: If result retrieval fails
        """
        url = f"{IF001_06_URL}/result"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        data = {
            "commonHeader": {
                "telegramId": telegram_id,
                "telegramType": TELEGRAM_TYPES["RESULT"],
                "mode": str(mode),
                "processId": process_id,
                "errorCode": "",
            }
        }

        try:
            response = requests.post(
                url, data=json.dumps(data), headers=headers, timeout=30
            )
            self._log_api_call("POST", url, headers, data, response)

            if response.status_code == 200:
                return response.json()
            else:
                raise MynaResultException(
                    f"Result request failed with status {response.status_code}: {response.text}"
                )

        except requests.exceptions.RequestException as e:
            raise MynaResultException(f"Network error during result request: {e}")
        except Exception as e:
            raise MynaResultException(f"Unexpected error during result request: {e}")

    def generate_telegram_id(self, date: Optional[str] = None) -> str:
        """
        Generate telegram ID for API requests.

        Format: TL-XXXXXXXX-YYMMDDHHMMSS-nnnn (29 chars)
        - If date (YYYYMMDD) is provided: use date[2:] as YYMMDD + current HHMMSS (for test env)
        - Otherwise: use full current datetime as YYMMDDHHMMSS
        - nnnn: unique sequence within the same second

        Returns:
            Generated telegram ID
        """
        now = datetime.now()
        hhmmss = now.strftime("%H%M%S")
        if date is not None:
            yymmddhhmmss = f"{date[2:]}{hhmmss}"
        else:
            yymmddhhmmss = now.strftime("%y%m%d%H%M%S")
        seq = _next_telegram_sequence(yymmddhhmmss)
        return f"TL-{SERVICE_PROVIDER_ID[2:]}-{yymmddhhmmss}-{seq:04d}"

    @staticmethod
    def get_inquiry_date() -> str:
        """
        Get the standard inquiry date.

        Returns:
            Date string for information inquiry
        """
        return INQUIRY_DATE
