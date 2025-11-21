"""
Token Manager
Manages OAuth2 tokens for Gmail accounts - validation, refresh, expiry checking.
"""

import os
import pickle
from datetime import datetime, timedelta
from typing import Optional, Dict
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from agent_platform.core.config import Config
from agent_platform.auth.models import AuthStatus
from agent_platform.events import log_event, EventType


class TokenManager:
    """Manages OAuth2 tokens for Gmail accounts."""

    def __init__(self):
        """Initialize TokenManager with account configurations."""
        self.accounts = Config.GMAIL_ACCOUNTS

    def get_credentials(self, account_id: str) -> Optional[Credentials]:
        """
        Load credentials for account.

        Args:
            account_id: Account identifier (gmail_1, gmail_2, gmail_3)

        Returns:
            Credentials object or None if not found/invalid
        """
        account_config = self.accounts.get(account_id)
        if not account_config:
            return None

        token_path = account_config.get('token_path')
        if not token_path or not os.path.exists(token_path):
            return None

        try:
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
                return creds
        except Exception as e:
            log_event(
                event_type=EventType.USER_FEEDBACK,  # Using existing type
                account_id=account_id,
                payload={'error': f'Failed to load token: {str(e)}'}
            )
            return None

    def save_credentials(self, account_id: str, creds: Credentials) -> bool:
        """
        Save credentials for account.

        Args:
            account_id: Account identifier
            creds: Credentials to save

        Returns:
            True if successful, False otherwise
        """
        account_config = self.accounts.get(account_id)
        if not account_config:
            return False

        token_path = account_config.get('token_path')
        if not token_path:
            return False

        try:
            # Ensure directory exists
            Path(token_path).parent.mkdir(parents=True, exist_ok=True)

            # Save token
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)

            log_event(
                event_type=EventType.USER_FEEDBACK,  # Using existing type
                account_id=account_id,
                payload={'action': 'token_saved', 'expires_at': creds.expiry.isoformat() if creds.expiry else None}
            )

            return True
        except Exception as e:
            log_event(
                event_type=EventType.USER_FEEDBACK,
                account_id=account_id,
                payload={'error': f'Failed to save token: {str(e)}'}
            )
            return False

    def is_valid(self, account_id: str) -> bool:
        """
        Check if account has valid credentials.

        Args:
            account_id: Account identifier

        Returns:
            True if credentials exist and are valid
        """
        creds = self.get_credentials(account_id)
        if not creds:
            return False

        return creds.valid

    def is_expired(self, account_id: str) -> bool:
        """
        Check if token is expired.

        Args:
            account_id: Account identifier

        Returns:
            True if expired, False if valid or no token
        """
        creds = self.get_credentials(account_id)
        if not creds:
            return True

        if not creds.expiry:
            return False  # No expiry info

        return creds.expired

    def get_expiry(self, account_id: str) -> Optional[datetime]:
        """
        Get token expiry datetime.

        Args:
            account_id: Account identifier

        Returns:
            Expiry datetime or None
        """
        creds = self.get_credentials(account_id)
        if not creds:
            return None

        return creds.expiry

    def expires_within(self, account_id: str, hours: int = 24) -> bool:
        """
        Check if token expires within specified hours.

        Args:
            account_id: Account identifier
            hours: Hours to check ahead

        Returns:
            True if expires within timeframe
        """
        expiry = self.get_expiry(account_id)
        if not expiry:
            return False

        threshold = datetime.utcnow() + timedelta(hours=hours)
        return expiry <= threshold

    def refresh_if_needed(self, account_id: str) -> bool:
        """
        Refresh token if expired or expiring soon.

        Args:
            account_id: Account identifier

        Returns:
            True if refreshed successfully or not needed
        """
        creds = self.get_credentials(account_id)
        if not creds:
            return False

        # If valid and not expiring soon, no refresh needed
        if creds.valid and not self.expires_within(account_id, hours=1):
            return True

        # Try to refresh
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self.save_credentials(account_id, creds)

                log_event(
                    event_type=EventType.USER_FEEDBACK,
                    account_id=account_id,
                    payload={
                        'action': 'token_refreshed',
                        'new_expiry': creds.expiry.isoformat() if creds.expiry else None
                    }
                )

                return True
            except Exception as e:
                log_event(
                    event_type=EventType.USER_FEEDBACK,
                    account_id=account_id,
                    payload={'error': f'Token refresh failed: {str(e)}'}
                )
                return False

        return False

    def revoke(self, account_id: str) -> bool:
        """
        Revoke token by deleting token file.

        Args:
            account_id: Account identifier

        Returns:
            True if revoked successfully
        """
        account_config = self.accounts.get(account_id)
        if not account_config:
            return False

        token_path = account_config.get('token_path')
        if not token_path or not os.path.exists(token_path):
            return True  # Already revoked

        try:
            os.remove(token_path)

            log_event(
                event_type=EventType.USER_FEEDBACK,
                account_id=account_id,
                payload={'action': 'token_revoked'}
            )

            return True
        except Exception as e:
            log_event(
                event_type=EventType.USER_FEEDBACK,
                account_id=account_id,
                payload={'error': f'Token revocation failed: {str(e)}'}
            )
            return False

    def get_auth_status(self, account_id: str) -> AuthStatus:
        """
        Get comprehensive authentication status for account.

        Args:
            account_id: Account identifier

        Returns:
            AuthStatus object with all status information
        """
        account_config = self.accounts.get(account_id)
        if not account_config:
            return AuthStatus(
                account_id=account_id,
                email="Unknown",
                authenticated=False,
                token_exists=False,
                credentials_exist=False,
                needs_reauth=True,
                error="Account not configured"
            )

        # Check credentials file
        creds_path = account_config.get('credentials_path', '')
        credentials_exist = os.path.exists(creds_path) if creds_path else False

        # Check token file
        token_path = account_config.get('token_path', '')
        token_exists = os.path.exists(token_path) if token_path else False

        # Get credentials
        creds = self.get_credentials(account_id)

        # Determine status
        authenticated = creds is not None and creds.valid
        expires_at = creds.expiry if creds else None
        needs_reauth = not authenticated or self.expires_within(account_id, hours=24)

        error = None
        if not credentials_exist:
            error = "Credentials file not found"
        elif not token_exists:
            error = "Token file not found - authentication required"
        elif creds and creds.expired and not creds.refresh_token:
            error = "Token expired and no refresh token available"

        return AuthStatus(
            account_id=account_id,
            email=account_config.get('email', 'Unknown'),
            authenticated=authenticated,
            token_exists=token_exists,
            credentials_exist=credentials_exist,
            expires_at=expires_at,
            needs_reauth=needs_reauth,
            error=error
        )

    def get_all_statuses(self) -> Dict[str, AuthStatus]:
        """
        Get authentication status for all configured accounts.

        Returns:
            Dictionary mapping account_id to AuthStatus
        """
        statuses = {}
        for account_id in self.accounts.keys():
            statuses[account_id] = self.get_auth_status(account_id)
        return statuses


# Singleton instance
_token_manager: Optional[TokenManager] = None


def get_token_manager() -> TokenManager:
    """
    Get singleton TokenManager instance.

    Returns:
        TokenManager instance
    """
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager()
    return _token_manager
