import os
from typing import Any, Dict


class GalileiConfigError(Exception):
    """Raised when Galilei configuration is invalid or missing"""


def get_galilei_config() -> Dict[str, Any]:
    """Get Galilei configuration from environment variables"""
    return {
        "client_auth_id": os.getenv("GALILEI_AUTH_CLIENT_ID", ""),
        "client_auth_user": os.getenv("GALILEI_AUTH_CLIENT_USER", ""),
        "client_auth_password": os.getenv("GALILEI_AUTH_CLIENT_PASSWORD", ""),
        "api_status_id": os.getenv("GALILEI_API_STATUS_ID", ""),
        "api_temperature_id": os.getenv("GALILEI_API_TEMPERATURE_ID", ""),
        "auth_flow": os.getenv("GALILEI_AUTH_FLOW", "USER_PASSWORD_AUTH"),
    }


def validate_galilei_config(config: Dict[str, Any]) -> bool:
    """Validate that all required configuration is present"""
    required_fields = [
        "client_auth_id",
        "client_auth_user",
        "client_auth_password",
        "api_status_id",
        "api_temperature_id",
    ]

    missing_fields = [field for field in required_fields if not config.get(field)]

    if missing_fields:
        raise GalileiConfigError(
            f"Missing required Galilei configuration: {', '.join(missing_fields)}. "
            f"Please set the following environment variables: "
            f"{', '.join([f'GALILEI_{field.upper()}' for field in missing_fields])}"
        )

    return True


# Get configuration
config = get_galilei_config()

# Validate configuration on import (optional - remove if you want lazy validation)
try:
    validate_galilei_config(config)
except GalileiConfigError as e:
    print(f"Warning: {e}")

# Public constants (non-sensitive)
GALILEI_API_STATUS_ID = config["api_status_id"]
GALILEI_API_TEMPERATURE_ID = config["api_temperature_id"]


# Authentication configuration factory
def get_auth_json() -> Dict[str, Any]:
    """Generate authentication JSON with current config"""
    current_config = get_galilei_config()
    validate_galilei_config(current_config)

    return {
        "ClientId": current_config["client_auth_id"],
        "AuthFlow": current_config["auth_flow"],
        "AuthParameters": {
            "USERNAME": current_config["client_auth_user"],
            "PASSWORD": current_config["client_auth_password"],
        },
    }
