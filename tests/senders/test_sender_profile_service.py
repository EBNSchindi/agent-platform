"""
Unit tests for Sender Profile Service.

Tests whitelist/blacklist management and preference application.
"""

import pytest
from agent_platform.senders.profile_service import SenderProfileService
from agent_platform.db.database import get_db
from agent_platform.db.models import SenderPreference


@pytest.fixture
def profile_service():
    """Create SenderProfileService instance."""
    return SenderProfileService()


@pytest.fixture
def cleanup_test_data():
    """Clean up test data after each test."""
    yield
    # Cleanup after test
    with get_db() as db:
        db.query(SenderPreference).filter(
            SenderPreference.sender_email.like('%@test-domain.com')
        ).delete()
        db.commit()


class TestWhitelistBlacklist:
    """Test whitelist and blacklist management."""

    @pytest.mark.asyncio
    async def test_whitelist_sender(self, profile_service, cleanup_test_data):
        """Test whitelisting a sender."""
        result = await profile_service.whitelist_sender(
            sender_email='important@test-domain.com',
            account_id='test_account'
        )

        assert result is not None
        assert result.is_whitelisted is True
        assert result.trust_level == 'trusted'
        assert result.sender_email == 'important@test-domain.com'

    @pytest.mark.asyncio
    async def test_blacklist_sender(self, profile_service, cleanup_test_data):
        """Test blacklisting a sender."""
        result = await profile_service.blacklist_sender(
            sender_email='spam@test-domain.com',
            account_id='test_account'
        )

        assert result is not None
        assert result.is_blacklisted is True
        assert result.trust_level == 'blocked'
        assert result.sender_email == 'spam@test-domain.com'

    @pytest.mark.asyncio
    async def test_set_trust_level(self, profile_service, cleanup_test_data):
        """Test setting trust level."""
        result = await profile_service.set_trust_level(
            sender_email='neutral@test-domain.com',
            account_id='test_account',
            trust_level='suspicious'
        )

        assert result is not None
        assert result.trust_level == 'suspicious'

    @pytest.mark.asyncio
    async def test_mute_categories(self, profile_service, cleanup_test_data):
        """Test muting categories for a sender."""
        result = await profile_service.mute_categories(
            sender_email='newsletter@test-domain.com',
            account_id='test_account',
            categories=['newsletter', 'werbung']
        )

        assert result is not None
        assert 'newsletter' in result.muted_categories
        assert 'werbung' in result.muted_categories

    @pytest.mark.asyncio
    async def test_allow_only_categories(self, profile_service, cleanup_test_data):
        """Test allowing only specific categories."""
        result = await profile_service.allow_only_categories(
            sender_email='work@test-domain.com',
            account_id='test_account',
            categories=['wichtig_todo', 'job_projekte']
        )

        assert result is not None
        assert 'wichtig_todo' in result.allowed_categories
        assert 'job_projekte' in result.allowed_categories

    @pytest.mark.asyncio
    async def test_set_preferred_category(self, profile_service, cleanup_test_data):
        """Test setting preferred primary category."""
        result = await profile_service.set_preferred_category(
            sender_email='boss@test-domain.com',
            account_id='test_account',
            category='wichtig_todo'
        )

        assert result is not None
        assert result.preferred_primary_category == 'wichtig_todo'


class TestPreferenceApplication:
    """Test applying preferences to classification results."""

    @pytest.mark.asyncio
    async def test_blacklist_forces_spam(self, profile_service, cleanup_test_data):
        """Test that blacklisted senders are forced to spam."""
        # First blacklist the sender
        await profile_service.blacklist_sender(
            sender_email='blacklisted@test-domain.com',
            account_id='test_account'
        )

        # Mock classification result
        classification_result = {
            'primary_category': 'wichtig_todo',
            'confidence': 0.90,
            'importance_score': 0.85
        }

        # Apply preferences
        result = await profile_service.apply_preferences(
            sender_email='blacklisted@test-domain.com',
            account_id='test_account',
            classification_result=classification_result
        )

        # Should be forced to spam
        assert result['primary_category'] == 'spam'
        assert result['confidence'] >= 0.95
        assert result['importance_score'] == 0.0

    @pytest.mark.asyncio
    async def test_whitelist_boosts_confidence(self, profile_service, cleanup_test_data):
        """Test that whitelisted senders get confidence boost."""
        # First whitelist the sender
        await profile_service.whitelist_sender(
            sender_email='trusted@test-domain.com',
            account_id='test_account'
        )

        # Mock classification result
        classification_result = {
            'primary_category': 'wichtig_todo',
            'confidence': 0.75,
            'importance_score': 0.85,
            'secondary_categories': []
        }

        original_confidence = classification_result['confidence']

        # Apply preferences
        result = await profile_service.apply_preferences(
            sender_email='trusted@test-domain.com',
            account_id='test_account',
            classification_result=classification_result
        )

        # Should get confidence boost
        assert result['confidence'] > original_confidence
        assert result['confidence'] <= 1.0

    @pytest.mark.asyncio
    async def test_muted_categories_reduce_importance(self, profile_service, cleanup_test_data):
        """Test that muted categories get importance reduction."""
        # First mute newsletter category
        await profile_service.mute_categories(
            sender_email='muted@test-domain.com',
            account_id='test_account',
            categories=['newsletter']
        )

        # Mock classification result with newsletter
        classification_result = {
            'primary_category': 'newsletter',
            'confidence': 0.80,
            'importance_score': 0.40,
            'secondary_categories': []
        }

        # Apply preferences
        result = await profile_service.apply_preferences(
            sender_email='muted@test-domain.com',
            account_id='test_account',
            classification_result=classification_result
        )

        # Should have reduced importance
        assert result['importance_score'] == 0.10

    @pytest.mark.asyncio
    async def test_no_preferences_returns_unchanged(self, profile_service, cleanup_test_data):
        """Test that unknown senders get unchanged classification."""
        classification_result = {
            'primary_category': 'wichtig_todo',
            'confidence': 0.85,
            'importance_score': 0.90,
            'secondary_categories': []
        }

        # Apply preferences (no profile exists)
        result = await profile_service.apply_preferences(
            sender_email='unknown@test-domain.com',
            account_id='test_account',
            classification_result=classification_result
        )

        # Should be unchanged
        assert result == classification_result

    @pytest.mark.asyncio
    async def test_preferred_category_override(self, profile_service, cleanup_test_data):
        """Test preferred category overrides classification."""
        # Set preferred category
        await profile_service.set_preferred_category(
            sender_email='override@test-domain.com',
            account_id='test_account',
            category='job_projekte'
        )

        classification_result = {
            'primary_category': 'newsletter',
            'confidence': 0.70,
            'importance_score': 0.40,
            'secondary_categories': []
        }

        # Apply preferences
        result = await profile_service.apply_preferences(
            sender_email='override@test-domain.com',
            account_id='test_account',
            classification_result=classification_result
        )

        # Should override to preferred category
        assert result['primary_category'] == 'job_projekte'


class TestProfileRetrieval:
    """Test profile retrieval and listing."""

    @pytest.mark.asyncio
    async def test_get_sender_profile(self, profile_service, cleanup_test_data):
        """Test retrieving sender profile."""
        # Create profile
        await profile_service.whitelist_sender(
            sender_email='profile@test-domain.com',
            account_id='test_account'
        )

        # Retrieve it
        profile = await profile_service.get_sender_profile(
            sender_email='profile@test-domain.com',
            account_id='test_account'
        )

        assert profile is not None
        assert profile.sender_email == 'profile@test-domain.com'
        assert profile.is_whitelisted is True

    @pytest.mark.asyncio
    async def test_list_whitelisted_senders(self, profile_service, cleanup_test_data):
        """Test listing whitelisted senders."""
        # Create multiple whitelisted senders
        await profile_service.whitelist_sender('white1@test-domain.com', 'test_account')
        await profile_service.whitelist_sender('white2@test-domain.com', 'test_account')

        # List them
        whitelisted = await profile_service.list_whitelisted(account_id='test_account')

        # Filter only test domain
        test_whitelisted = [p for p in whitelisted if '@test-domain.com' in p.sender_email]
        assert len(test_whitelisted) >= 2

    @pytest.mark.asyncio
    async def test_list_blacklisted_senders(self, profile_service, cleanup_test_data):
        """Test listing blacklisted senders."""
        # Create multiple blacklisted senders
        await profile_service.blacklist_sender('black1@test-domain.com', 'test_account')
        await profile_service.blacklist_sender('black2@test-domain.com', 'test_account')

        # List them
        blacklisted = await profile_service.list_blacklisted(account_id='test_account')

        # Filter only test domain
        test_blacklisted = [p for p in blacklisted if '@test-domain.com' in p.sender_email]
        assert len(test_blacklisted) >= 2
