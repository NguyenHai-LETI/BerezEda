"""Custom exceptions for MynaPortal API operations."""

from typing import Optional


class MynaPortalException(Exception):
    """Base exception for MynaPortal operations."""

    def __init__(self, message: str, error_code: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class MynaTokenException(MynaPortalException):
    """Exception raised when token acquisition fails."""


class MynaRequestException(MynaPortalException):
    """Exception raised when API request fails."""


class MynaResultException(MynaPortalException):
    """Exception raised when result retrieval fails."""


class MynaDataValidationException(MynaPortalException):
    """Exception raised when data validation fails."""


class MynaAuthorizerNotFoundException(MynaPortalException):
    """Exception raised when MynaAuthorizer record is not found."""
