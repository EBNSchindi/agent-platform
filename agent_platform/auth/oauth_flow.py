"""
OAuth Flow Manager
Handles OAuth2 authorization flow - URL generation, state management, callback processing.
"""

import os
import secrets
from typing import Optional, Dict
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from agent_platform.core.config import Config
from agent_platform.auth.token_manager import get_token_manager
from agent_platform.auth.models import (
    OAuthUrlResponse,
    OAuthCallbackResponse,
)
from agent_platform.events import log_event, EventType


# Scopes for Gmail API
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify'
]

# State tokens cache (in-memory, expires after 1 hour)
# Format: {state_token: {'account_id': str, 'created_at': datetime}}
_state_tokens: Dict[str, Dict] = {}


class OAuthFlowManager:
    """Manages OAuth2 authorization flow for Gmail accounts."""

    def __init__(self):
        """Initialize OAuthFlowManager."""
        self.accounts = Config.GMAIL_ACCOUNTS
        self.token_manager = get_token_manager()

    def generate_auth_url(
        self,
        account_id: str,
        redirect_uri: str = "http://localhost:3000/auth/callback"
    ) -> Optional[OAuthUrlResponse]:
        """
        Generate OAuth authorization URL for account.

        Args:
            account_id: Account identifier (gmail_1, gmail_2, gmail_3)
            redirect_uri: OAuth redirect URI (default: Next.js frontend)

        Returns:
            OAuthUrlResponse with auth_url and state token, or None if account not found
        """
        account_config = self.accounts.get(account_id)
        if not account_config:
            return None

        credentials_path = account_config.get('credentials_path')
        if not credentials_path or not os.path.exists(credentials_path):
            return None

        try:
            # Create flow
            flow = Flow.from_client_secrets_file(
                credentials_path,
                scopes=SCOPES,
                redirect_uri=redirect_uri
            )

            # Generate state token for CSRF protection
            state_token = secrets.token_urlsafe(32)

            # Generate authorization URL
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=state_token,
                prompt='consent'  # Force consent to get refresh token
            )

            # Cache state token
            _state_tokens[state_token] = {
                'account_id': account_id,
                'created_at': datetime.utcnow(),
                'redirect_uri': redirect_uri
            }

            # Clean old state tokens (older than 1 hour)
            self._clean_expired_state_tokens()

            log_event(
                event_type=EventType.USER_FEEDBACK,
                account_id=account_id,
                payload={'action': 'oauth_url_generated', 'redirect_uri': redirect_uri}
            )

            return OAuthUrlResponse(
                auth_url=auth_url,
                state=state_token,
                account_id=account_id,
                message=f"Please visit the auth_url to authorize {account_config.get('email')}"
            )

        except Exception as e:
            log_event(
                event_type=EventType.USER_FEEDBACK,
                account_id=account_id,
                payload={'error': f'Failed to generate OAuth URL: {str(e)}'}
            )
            return None

    def handle_callback(
        self,
        code: str,
        state: str,
        redirect_uri: str = "http://localhost:3000/auth/callback"
    ) -> Optional[OAuthCallbackResponse]:
        """
        Handle OAuth callback - exchange authorization code for tokens.

        Args:
            code: Authorization code from OAuth provider
            state: State token for CSRF validation
            redirect_uri: Must match the one used in generate_auth_url

        Returns:
            OAuthCallbackResponse with success status, or None if invalid
        """
        # Validate state token
        state_data = _state_tokens.get(state)
        if not state_data:
            return OAuthCallbackResponse(
                success=False,
                message="Invalid or expired state token",
                account_id="unknown"
            )

        account_id = state_data['account_id']
        cached_redirect_uri = state_data.get('redirect_uri', redirect_uri)

        # Remove used state token
        del _state_tokens[state]

        # Get account config
        account_config = self.accounts.get(account_id)
        if not account_config:
            return OAuthCallbackResponse(
                success=False,
                message=f"Account {account_id} not found",
                account_id=account_id
            )

        credentials_path = account_config.get('credentials_path')
        if not credentials_path or not os.path.exists(credentials_path):
            return OAuthCallbackResponse(
                success=False,
                message="Credentials file not found",
                account_id=account_id
            )

        try:
            # Create flow with same redirect URI
            flow = Flow.from_client_secrets_file(
                credentials_path,
                scopes=SCOPES,
                redirect_uri=cached_redirect_uri
            )

            # Exchange authorization code for credentials
            flow.fetch_token(code=code)

            # Get credentials
            credentials = flow.credentials

            # Save credentials
            success = self.token_manager.save_credentials(account_id, credentials)

            if not success:
                return OAuthCallbackResponse(
                    success=False,
                    message="Failed to save credentials",
                    account_id=account_id
                )

            log_event(
                event_type=EventType.USER_FEEDBACK,
                account_id=account_id,
                payload={
                    'action': 'oauth_callback_success',
                    'expires_at': credentials.expiry.isoformat() if credentials.expiry else None
                }
            )

            return OAuthCallbackResponse(
                success=True,
                message=f"Successfully authenticated {account_config.get('email')}",
                account_id=account_id,
                expires_at=credentials.expiry
            )

        except Exception as e:
            log_event(
                event_type=EventType.USER_FEEDBACK,
                account_id=account_id,
                payload={'error': f'OAuth callback failed: {str(e)}'}
            )

            return OAuthCallbackResponse(
                success=False,
                message=f"Authentication failed: {str(e)}",
                account_id=account_id
            )

    def _clean_expired_state_tokens(self):
        """Remove state tokens older than 1 hour."""
        cutoff = datetime.utcnow() - timedelta(hours=1)
        expired_tokens = [
            token
            for token, data in _state_tokens.items()
            if data['created_at'] < cutoff
        ]

        for token in expired_tokens:
            del _state_tokens[token]


# Singleton instance
_oauth_flow_manager: Optional[OAuthFlowManager] = None


def get_oauth_flow_manager() -> OAuthFlowManager:
    """
    Get singleton OAuthFlowManager instance.

    Returns:
        OAuthFlowManager instance
    """
    global _oauth_flow_manager
    if _oauth_flow_manager is None:
        _oauth_flow_manager = OAuthFlowManager()
    return _oauth_flow_manager
