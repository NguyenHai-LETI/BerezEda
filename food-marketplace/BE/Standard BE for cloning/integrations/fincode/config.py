"""Fincode API configuration settings."""

import os

# API Configuration
FINCODE_API_BASE_URL = os.getenv("FINCODE_API_BASE_URL", "https://api.test.fincode.jp")
FINCODE_PUBLIC_KEY = os.getenv(
    "FINCODE_PUBLIC_KEY",
    "p_test_NDkwZjk5N2UtNzczYS00ZmUxLWE5MjctNWMxNmY1OGFhODBhMGIxMDE4OWItZDBlNy00ZTA2LTlhMTctYzcxMGUxMDM2Y2E4c18yNTA5Mjc3OTIxMA",
)
FINCODE_SECRET_KEY = os.getenv(
    "FINCODE_SECRET_KEY",
    "m_test_NzE0MGQ3YTctMWQwNC00ZDcxLWJhMmEtZjc0NGI4YmVlYmMzMjAxNGE3YWUtMzc4NC00MWZlLTkwMjEtZmJjYzUxNDY3ODY1c18yNDExMDE5NDE4MA",
)
FINCODE_IS_LIVE_MODE = os.getenv("FINCODE_IS_LIVE_MODE", "false").lower() == "true"

# API Endpoints
FINCODE_PAYMENTS_ENDPOINT = f"{FINCODE_API_BASE_URL}/v1/payments"
FINCODE_CUSTOMERS_ENDPOINT = f"{FINCODE_API_BASE_URL}/v1/customers"
FINCODE_CARDS_ENDPOINT = f"{FINCODE_API_BASE_URL}/v1/customers/{{customer_id}}/cards"
FINCODE_CARD_TOKEN_ENDPOINT = f"{FINCODE_API_BASE_URL}/v1/card/token"
FINCODE_CARD_SESSIONS_ENDPOINT = f"{FINCODE_API_BASE_URL}/v1/card_sessions"
FINCODE_PAYMENT_REGISTRATION_ENDPOINT = f"{FINCODE_API_BASE_URL}/v1/payments"
FINCODE_PAYMENT_EXECUTION_ENDPOINT = (
    f"{FINCODE_API_BASE_URL}/v1/payments/{{payment_id}}"
)

# Webhook Configuration
FINCODE_WEBHOOK_SECRET = os.getenv("FINCODE_WEBHOOK_SECRET", "")

# Error Messages
ERROR_MESSAGES = {
    "INVALID_CARD_TOKEN": "Invalid card token provided",
    "PAYMENT_REGISTRATION_FAILED": "Failed to register payment with Fincode",
    "PAYMENT_EXECUTION_FAILED": "Failed to execute payment",
    "INVALID_AMOUNT": "Invalid payment amount",
    "INVALID_CUSTOMER_ID": "Invalid customer ID",
    "PAYMENT_NOT_FOUND": "Payment not found",
    "CARD_TOKENIZATION_FAILED": "Failed to tokenize card information",
    "INSUFFICIENT_FUNDS": "Insufficient funds",
    "CARD_DECLINED": "Card was declined",
    "EXPIRED_CARD": "Card has expired",
    "INVALID_CVV": "Invalid CVV code",
    "NETWORK_ERROR": "Network error occurred during payment processing",
    "TIMEOUT_ERROR": "Payment request timed out",
    "UNAUTHORIZED": "Unauthorized access to Fincode API",
    "RATE_LIMITED": "Too many requests, please try again later",
}

# Response Headers
DEFAULT_HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


def get_auth_headers(secret_key: str = None) -> dict:
    """Get authentication headers for Fincode API requests."""
    key = secret_key or FINCODE_SECRET_KEY
    return {**DEFAULT_HEADERS, "Authorization": f"Bearer {key}"}
