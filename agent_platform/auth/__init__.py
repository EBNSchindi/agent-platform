"""
Authentication Module
Handles OAuth2 authentication for Gmail accounts.
"""

from agent_platform.auth.token_manager import TokenManager, get_token_manager
from agent_platform.auth.oauth_flow import OAuthFlowManager, get_oauth_flow_manager
from agent_platform.auth.models import (
    AccountStatus,
    AuthStatus,
    OAuthUrlResponse,
    OAuthCallbackRequest,
    OAuthCallbackResponse,
    TokenRefreshResponse,
    TokenRevokeResponse,
)

__all__ = [
    'TokenManager',
    'get_token_manager',
    'OAuthFlowManager',
    'get_oauth_flow_manager',
    'AccountStatus',
    'AuthStatus',
    'OAuthUrlResponse',
    'OAuthCallbackRequest',
    'OAuthCallbackResponse',
    'TokenRefreshResponse',
    'TokenRevokeResponse',
]
