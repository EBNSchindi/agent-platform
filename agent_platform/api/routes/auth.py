"""
Authentication API Routes
OAuth management endpoints for Gmail accounts.
"""

from typing import List
from fastapi import APIRouter, HTTPException, Query

from agent_platform.auth import (
    get_token_manager,
    get_oauth_flow_manager,
    AccountStatus,
    AuthStatus,
    OAuthUrlResponse,
    OAuthCallbackRequest,
    OAuthCallbackResponse,
    TokenRefreshResponse,
    TokenRevokeResponse,
)
from agent_platform.auth.oauth_flow import OAuthFlowManager


router = APIRouter()


@router.get("/auth/accounts", response_model=AccountStatus)
def list_accounts():
    """
    List all configured Gmail accounts with authentication status.

    Returns:
        AccountStatus with list of all accounts and summary counts
    """
    token_manager = get_token_manager()
    statuses_dict = token_manager.get_all_statuses()

    accounts = list(statuses_dict.values())
    authenticated_count = sum(1 for a in accounts if a.authenticated)
    needs_reauth_count = sum(1 for a in accounts if a.needs_reauth)

    return AccountStatus(
        accounts=accounts,
        total=len(accounts),
        authenticated_count=authenticated_count,
        needs_reauth_count=needs_reauth_count
    )


@router.get("/auth/gmail/{account_id}/status", response_model=AuthStatus)
def get_auth_status(account_id: str):
    """
    Get authentication status for specific Gmail account.

    Args:
        account_id: Account identifier (gmail_1, gmail_2, gmail_3)

    Returns:
        AuthStatus with detailed authentication information

    Raises:
        404: Account not found
    """
    token_manager = get_token_manager()
    status = token_manager.get_auth_status(account_id)

    if status.error == "Account not configured":
        raise HTTPException(
            status_code=404,
            detail=f"Account {account_id} not found"
        )

    return status


@router.get("/auth/gmail/{account_id}/authorize", response_model=OAuthUrlResponse)
def start_oauth_flow(
    account_id: str,
    redirect_uri: str = Query("http://localhost:3000/auth/callback", description="OAuth redirect URI")
):
    """
    Start OAuth flow - generate authorization URL.

    Args:
        account_id: Account identifier (gmail_1, gmail_2, gmail_3)
        redirect_uri: OAuth callback URL (default: Next.js frontend)

    Returns:
        OAuthUrlResponse with auth_url and state token

    Raises:
        404: Account not found
        500: Failed to generate OAuth URL

    Example:
        GET /api/v1/auth/gmail/gmail_1/authorize

        Response:
        {
            "auth_url": "https://accounts.google.com/o/oauth2/auth?...",
            "state": "abc123...",
            "account_id": "gmail_1",
            "message": "Please visit the auth_url to authorize user@gmail.com"
        }

    Frontend Usage:
        1. Call this endpoint to get auth_url
        2. Open auth_url in popup or new tab
        3. User completes OAuth consent
        4. Google redirects to redirect_uri with code and state
        5. Frontend calls POST /auth/gmail/{account_id}/callback with code and state
    """
    oauth_manager = get_oauth_flow_manager()
    response = oauth_manager.generate_auth_url(account_id, redirect_uri)

    if not response:
        # Check if account exists
        token_manager = get_token_manager()
        status = token_manager.get_auth_status(account_id)

        if status.error == "Account not configured":
            raise HTTPException(
                status_code=404,
                detail=f"Account {account_id} not found"
            )
        elif not status.credentials_exist:
            raise HTTPException(
                status_code=500,
                detail=f"Credentials file not found for {account_id}"
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate OAuth URL for {account_id}"
            )

    return response


@router.post("/auth/gmail/{account_id}/callback", response_model=OAuthCallbackResponse)
def handle_oauth_callback(
    account_id: str,
    request: OAuthCallbackRequest,
    redirect_uri: str = Query("http://localhost:3000/auth/callback", description="OAuth redirect URI")
):
    """
    Handle OAuth callback - exchange authorization code for tokens.

    Args:
        account_id: Account identifier (gmail_1, gmail_2, gmail_3)
        request: OAuth callback request with code and state
        redirect_uri: Must match the redirect_uri used in /authorize

    Returns:
        OAuthCallbackResponse with success status and expiry

    Raises:
        400: Invalid or expired state token
        500: Failed to exchange code for tokens

    Example:
        POST /api/v1/auth/gmail/gmail_1/callback
        Body: {
            "code": "4/0AY0e-...",
            "state": "abc123..."
        }

        Response:
        {
            "success": true,
            "message": "Successfully authenticated user@gmail.com",
            "account_id": "gmail_1",
            "expires_at": "2025-11-22T10:30:00Z"
        }
    """
    oauth_manager = get_oauth_flow_manager()
    response = oauth_manager.handle_callback(
        code=request.code,
        state=request.state,
        redirect_uri=redirect_uri
    )

    if not response:
        raise HTTPException(
            status_code=500,
            detail="Failed to process OAuth callback"
        )

    if not response.success:
        if "Invalid or expired state" in response.message:
            raise HTTPException(
                status_code=400,
                detail=response.message
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=response.message
            )

    return response


@router.post("/auth/gmail/{account_id}/refresh", response_model=TokenRefreshResponse)
def refresh_token(account_id: str):
    """
    Manually refresh access token for account.

    Args:
        account_id: Account identifier (gmail_1, gmail_2, gmail_3)

    Returns:
        TokenRefreshResponse with success status and new expiry

    Raises:
        404: Account not found
        400: Token refresh not possible (no refresh token)

    Example:
        POST /api/v1/auth/gmail/gmail_1/refresh

        Response:
        {
            "success": true,
            "message": "Token refreshed successfully",
            "account_id": "gmail_1",
            "expires_at": "2025-11-22T11:00:00Z",
            "refreshed": true
        }
    """
    token_manager = get_token_manager()

    # Check if account exists
    status = token_manager.get_auth_status(account_id)
    if status.error == "Account not configured":
        raise HTTPException(
            status_code=404,
            detail=f"Account {account_id} not found"
        )

    # Try to refresh
    success = token_manager.refresh_if_needed(account_id)

    if not success:
        # Check why it failed
        creds = token_manager.get_credentials(account_id)
        if not creds:
            raise HTTPException(
                status_code=400,
                detail="No credentials found - full re-authentication required"
            )
        elif not creds.refresh_token:
            raise HTTPException(
                status_code=400,
                detail="No refresh token available - full re-authentication required"
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Token refresh failed"
            )

    # Get new expiry
    expiry = token_manager.get_expiry(account_id)

    return TokenRefreshResponse(
        success=True,
        message="Token refreshed successfully",
        account_id=account_id,
        expires_at=expiry,
        refreshed=True
    )


@router.delete("/auth/gmail/{account_id}/revoke", response_model=TokenRevokeResponse)
def revoke_token(account_id: str):
    """
    Revoke token for account (delete token file).

    Args:
        account_id: Account identifier (gmail_1, gmail_2, gmail_3)

    Returns:
        TokenRevokeResponse with success status

    Raises:
        404: Account not found

    Example:
        DELETE /api/v1/auth/gmail/gmail_1/revoke

        Response:
        {
            "success": true,
            "message": "Token revoked successfully",
            "account_id": "gmail_1"
        }

    Note:
        This only deletes the local token file. The token is not revoked
        with Google - the user must revoke access in Google Account settings
        for full revocation.
    """
    token_manager = get_token_manager()

    # Check if account exists
    status = token_manager.get_auth_status(account_id)
    if status.error == "Account not configured":
        raise HTTPException(
            status_code=404,
            detail=f"Account {account_id} not found"
        )

    # Revoke token
    success = token_manager.revoke(account_id)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to revoke token"
        )

    return TokenRevokeResponse(
        success=True,
        message="Token revoked successfully - full re-authentication required",
        account_id=account_id
    )
