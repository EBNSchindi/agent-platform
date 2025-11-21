"""
Authentication Models
Pydantic models for OAuth authentication responses.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class AuthStatus(BaseModel):
    """Authentication status for a single account."""
    account_id: str
    email: str
    authenticated: bool
    token_exists: bool
    credentials_exist: bool
    expires_at: Optional[datetime] = None
    needs_reauth: bool = False
    error: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class AccountStatus(BaseModel):
    """List of all account statuses."""
    accounts: List[AuthStatus]
    total: int
    authenticated_count: int
    needs_reauth_count: int


class OAuthUrlResponse(BaseModel):
    """Response containing OAuth authorization URL."""
    auth_url: str
    state: str = Field(..., description="CSRF state token for validation")
    account_id: str
    message: str = "Please visit the auth_url to authorize"


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request with authorization code."""
    code: str = Field(..., description="Authorization code from OAuth provider")
    state: str = Field(..., description="CSRF state token for validation")


class OAuthCallbackResponse(BaseModel):
    """Response after processing OAuth callback."""
    success: bool
    message: str
    account_id: str
    expires_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class TokenRefreshResponse(BaseModel):
    """Response after token refresh."""
    success: bool
    message: str
    account_id: str
    expires_at: Optional[datetime] = None
    refreshed: bool = False

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class TokenRevokeResponse(BaseModel):
    """Response after token revocation."""
    success: bool
    message: str
    account_id: str
