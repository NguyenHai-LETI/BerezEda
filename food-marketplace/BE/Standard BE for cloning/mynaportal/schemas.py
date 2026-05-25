"""Schemas for MynaPortal API requests and responses."""

from typing import Optional

from pydantic import BaseModel


class MynaAuthorizerCreateRequest(BaseModel):
    """Request schema for creating a MynaAuthorizer."""


class MynaAuthorizerResponse(BaseModel):
    """Response schema for MynaAuthorizer creation."""

    link_authorize: str


class MynaCallbackRequest(BaseModel):
    """Request schema for MynaPortal callback."""

    commonHeader: dict


class MyNumberCallbackRequest(BaseModel):
    """Request schema for MyNumber callback from MynaPortal."""

    state: Optional[str] = None
    code: Optional[str] = None


class MyNumberResponse(BaseModel):
    """Response schema for MyNumber processing."""

    message: str
    deeplink: str
    html_content: str
