"""
Dynamic Account Registry

Automatically discovers email accounts from multiple sources:
1. Token files in tokens/ directory
2. Environment variables (GMAIL_*_EMAIL, IONOS_EMAIL)
3. Database records (unique account_ids in ProcessedEmail)

Provides a unified interface for account discovery without hardcoding account lists.
"""

import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass
from agent_platform.db.database import get_db
from agent_platform.db.models import ProcessedEmail
from sqlalchemy import select, func


@dataclass
class AccountInfo:
    """Information about a discovered email account."""
    account_id: str
    email: str
    account_type: str  # 'gmail', 'ionos', 'unknown'
    has_token: bool
    last_seen: Optional[datetime] = None
    email_count: int = 0


class AccountRegistry:
    """
    Registry for dynamically discovering and managing email accounts.

    Discovers accounts from:
    - Token files (*.json, *.pickle)
    - Environment variables
    - Database records

    Caches results for performance (5-minute TTL).
    """

    def __init__(self, cache_ttl_seconds: int = 300):
        """
        Initialize the account registry.

        Args:
            cache_ttl_seconds: Cache time-to-live in seconds (default: 5 minutes)
        """
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self._cache: Optional[List[AccountInfo]] = None
        self._cache_timestamp: Optional[datetime] = None

        # Project root directory
        self.project_root = Path(__file__).parent.parent.parent
        self.tokens_dir = self.project_root / "tokens"
        self.credentials_dir = self.project_root / "credentials"

    def get_all_accounts(self, force_refresh: bool = False) -> List[AccountInfo]:
        """
        Get all discovered email accounts.

        Args:
            force_refresh: Force cache refresh even if not expired

        Returns:
            List of AccountInfo objects
        """
        # Check cache
        if not force_refresh and self._is_cache_valid():
            return self._cache

        # Discover accounts from all sources
        accounts = self._discover_accounts()

        # Update cache
        self._cache = accounts
        self._cache_timestamp = datetime.now()

        return accounts

    def get_account(self, account_id: str) -> Optional[AccountInfo]:
        """
        Get information for a specific account.

        Args:
            account_id: Account identifier (e.g., 'gmail_1', 'ionos')

        Returns:
            AccountInfo if found, None otherwise
        """
        accounts = self.get_all_accounts()
        for account in accounts:
            if account.account_id == account_id:
                return account
        return None

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._cache is None or self._cache_timestamp is None:
            return False

        age = datetime.now() - self._cache_timestamp
        return age < self.cache_ttl

    def _discover_accounts(self) -> List[AccountInfo]:
        """
        Discover accounts from all sources.

        Returns:
            List of discovered AccountInfo objects
        """
        accounts_dict: Dict[str, AccountInfo] = {}

        # 1. Discover from token files
        token_accounts = self._discover_from_tokens()
        for acc in token_accounts:
            accounts_dict[acc.account_id] = acc

        # 2. Discover from environment variables
        env_accounts = self._discover_from_env()
        for acc in env_accounts:
            if acc.account_id in accounts_dict:
                # Merge: keep token info, update email from env
                accounts_dict[acc.account_id].email = acc.email
            else:
                accounts_dict[acc.account_id] = acc

        # 3. Enrich with database statistics
        self._enrich_from_database(accounts_dict)

        # Sort by account_id for consistent ordering
        return sorted(accounts_dict.values(), key=lambda x: x.account_id)

    def _discover_from_tokens(self) -> List[AccountInfo]:
        """
        Discover accounts from token files in tokens/ directory.

        Looks for patterns:
        - gmail_1_token.json, gmail_2_token.pickle, etc.
        - ionos_token.json

        Returns:
            List of AccountInfo objects
        """
        accounts = []

        if not self.tokens_dir.exists():
            return accounts

        # Pattern: {account_id}_token.{json|pickle}
        pattern = re.compile(r'^(.+?)_token\.(json|pickle)$')

        for file in self.tokens_dir.iterdir():
            if file.is_file():
                match = pattern.match(file.name)
                if match:
                    account_id = match.group(1)
                    account_type = self._determine_account_type(account_id)

                    accounts.append(AccountInfo(
                        account_id=account_id,
                        email=f"{account_id}@unknown.com",  # Will be updated from env
                        account_type=account_type,
                        has_token=True
                    ))

        return accounts

    def _discover_from_env(self) -> List[AccountInfo]:
        """
        Discover accounts from environment variables.

        Looks for patterns:
        - GMAIL_1_EMAIL, GMAIL_2_EMAIL, GMAIL_3_EMAIL, ...
        - IONOS_EMAIL

        Returns:
            List of AccountInfo objects
        """
        accounts = []

        # Pattern: GMAIL_{N}_EMAIL
        gmail_pattern = re.compile(r'^GMAIL_(\d+)_EMAIL$')

        for key, value in os.environ.items():
            # Check for Gmail accounts
            match = gmail_pattern.match(key)
            if match:
                num = match.group(1)
                account_id = f"gmail_{num}"
                accounts.append(AccountInfo(
                    account_id=account_id,
                    email=value,
                    account_type='gmail',
                    has_token=False  # Will be updated if token exists
                ))

            # Check for Ionos account
            elif key == 'IONOS_EMAIL':
                accounts.append(AccountInfo(
                    account_id='ionos',
                    email=value,
                    account_type='ionos',
                    has_token=False
                ))

        return accounts

    def _enrich_from_database(self, accounts_dict: Dict[str, AccountInfo]) -> None:
        """
        Enrich account information from database.

        Updates:
        - last_seen: Most recent email timestamp
        - email_count: Number of processed emails

        Also discovers accounts that exist only in database.

        Args:
            accounts_dict: Dictionary of account_id -> AccountInfo to enrich
        """
        try:
            with get_db() as db:
                # Get statistics per account
                query = (
                    select(
                        ProcessedEmail.account_id,
                        func.count(ProcessedEmail.id).label('email_count'),
                        func.max(ProcessedEmail.received_at).label('last_seen')
                    )
                    .group_by(ProcessedEmail.account_id)
                )

                results = db.execute(query).all()

                for row in results:
                    # Convert account_id to string (may be int in DB)
                    account_id = str(row.account_id)

                    if account_id in accounts_dict:
                        # Enrich existing account (only configured accounts)
                        accounts_dict[account_id].last_seen = row.last_seen
                        accounts_dict[account_id].email_count = row.email_count
                    # else:
                    #     # DISABLED: Don't auto-discover accounts from database
                    #     # This was adding test/dummy accounts to the UI
                    #     # Only show accounts configured in .env or with token files
                    #     account_type = self._determine_account_type(account_id)
                    #     accounts_dict[account_id] = AccountInfo(
                    #         account_id=account_id,
                    #         email=f"{account_id}@unknown.com",
                    #         account_type=account_type,
                    #         has_token=False,
                    #         last_seen=row.last_seen,
                    #         email_count=row.email_count
                    #     )

        except Exception as e:
            # Log error but don't fail discovery
            print(f"Warning: Could not enrich accounts from database: {e}")

    def _determine_account_type(self, account_id: str) -> str:
        """
        Determine account type from account_id.

        Args:
            account_id: Account identifier

        Returns:
            'gmail', 'ionos', or 'unknown'
        """
        if account_id.startswith('gmail_'):
            return 'gmail'
        elif account_id.startswith('ionos'):
            return 'ionos'
        else:
            return 'unknown'


# Global registry instance
_registry: Optional[AccountRegistry] = None


def get_account_registry() -> AccountRegistry:
    """
    Get the global account registry instance.

    Returns:
        AccountRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = AccountRegistry()
    return _registry
