"""
Account Management API Routes

Provides endpoints for discovering and managing email accounts dynamically.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from agent_platform.core.account_registry import get_account_registry, AccountInfo


router = APIRouter()


# Pydantic Models

class AccountResponse(BaseModel):
    """Response model for account information."""
    account_id: str = Field(..., description="Unique account identifier (e.g., 'gmail_1', 'ionos')")
    email: str = Field(..., description="Email address associated with the account")
    account_type: str = Field(..., description="Account type: 'gmail', 'ionos', or 'unknown'")
    has_token: bool = Field(..., description="Whether OAuth token exists for this account")
    last_seen: Optional[datetime] = Field(None, description="Timestamp of most recent email from this account")
    email_count: int = Field(0, description="Number of processed emails for this account")


class AccountListResponse(BaseModel):
    """Response model for list of accounts."""
    accounts: List[AccountResponse]
    total: int = Field(..., description="Total number of discovered accounts")


# API Routes

@router.get("/accounts", response_model=AccountListResponse)
def list_accounts(
    force_refresh: bool = Query(False, description="Force cache refresh")
):
    """
    List all discovered email accounts.

    Discovers accounts from:
    - Token files in tokens/ directory
    - Environment variables (GMAIL_*_EMAIL, IONOS_EMAIL)
    - Database records (ProcessedEmail table)

    Results are cached for 5 minutes for performance.

    **Example Request:**
    ```
    GET /api/v1/accounts
    GET /api/v1/accounts?force_refresh=true
    ```

    **Example Response:**
    ```json
    {
      "accounts": [
        {
          "account_id": "gmail_1",
          "email": "user@gmail.com",
          "account_type": "gmail",
          "has_token": true,
          "last_seen": "2025-11-21T10:30:00",
          "email_count": 1523
        },
        {
          "account_id": "gmail_2",
          "email": "work@gmail.com",
          "account_type": "gmail",
          "has_token": true,
          "last_seen": "2025-11-21T09:15:00",
          "email_count": 892
        },
        {
          "account_id": "ionos",
          "email": "info@company.de",
          "account_type": "ionos",
          "has_token": false,
          "last_seen": "2025-11-20T18:45:00",
          "email_count": 234
        }
      ],
      "total": 3
    }
    ```

    **Use Cases:**
    - Populate account selector dropdown in frontend
    - Display account statistics in dashboard
    - Validate account_id before fetching emails
    - Auto-discover new accounts without code changes

    **Dynamic Behavior:**
    - New accounts added to .env appear automatically
    - Accounts removed from system disappear from list
    - No hardcoded account lists in frontend code
    """
    try:
        registry = get_account_registry()
        accounts = registry.get_all_accounts(force_refresh=force_refresh)

        account_responses = [
            AccountResponse(
                account_id=acc.account_id,
                email=acc.email,
                account_type=acc.account_type,
                has_token=acc.has_token,
                last_seen=acc.last_seen,
                email_count=acc.email_count
            )
            for acc in accounts
        ]

        return AccountListResponse(
            accounts=account_responses,
            total=len(account_responses)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to discover accounts: {str(e)}"
        )


@router.get("/accounts/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: str,
    force_refresh: bool = Query(False, description="Force cache refresh")
):
    """
    Get information for a specific account.

    **Example Request:**
    ```
    GET /api/v1/accounts/gmail_1
    ```

    **Example Response:**
    ```json
    {
      "account_id": "gmail_1",
      "email": "user@gmail.com",
      "account_type": "gmail",
      "has_token": true,
      "last_seen": "2025-11-21T10:30:00",
      "email_count": 1523
    }
    ```

    **Error Responses:**
    - 404: Account not found
    - 500: Server error during discovery
    """
    try:
        registry = get_account_registry()

        if force_refresh:
            registry.get_all_accounts(force_refresh=True)

        account = registry.get_account(account_id)

        if not account:
            raise HTTPException(
                status_code=404,
                detail=f"Account '{account_id}' not found. Available accounts can be listed via GET /accounts"
            )

        return AccountResponse(
            account_id=account.account_id,
            email=account.email,
            account_type=account.account_type,
            has_token=account.has_token,
            last_seen=account.last_seen,
            email_count=account.email_count
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get account info: {str(e)}"
        )


@router.post("/accounts/refresh")
def refresh_account_cache():
    """
    Force refresh of account cache.

    Useful after:
    - Adding new accounts to .env
    - Changing token files
    - Database updates

    **Example Request:**
    ```
    POST /api/v1/accounts/refresh
    ```

    **Example Response:**
    ```json
    {
      "message": "Account cache refreshed successfully",
      "accounts_discovered": 3
    }
    ```
    """
    try:
        registry = get_account_registry()
        accounts = registry.get_all_accounts(force_refresh=True)

        return {
            "message": "Account cache refreshed successfully",
            "accounts_discovered": len(accounts)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh account cache: {str(e)}"
        )
