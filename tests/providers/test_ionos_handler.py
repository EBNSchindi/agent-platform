"""
Unit tests for IONOS Handler.

Tests IONOS-specific single-folder IMAP operations.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from agent_platform.providers.ionos_handler import IonosHandler, CATEGORY_TO_FOLDER_MAP


@pytest.fixture
def ionos_handler():
    """Create IonosHandler instance."""
    return IonosHandler()


class TestCategoryMapping:
    """Test category to IONOS folder mapping."""

    def test_all_categories_mapped(self):
        """Test that all 10 categories have folder mappings."""
        expected_categories = [
            'wichtig_todo', 'termine', 'finanzen', 'bestellungen',
            'job_projekte', 'vertraege', 'persoenlich', 'newsletter',
            'werbung', 'spam'
        ]

        for category in expected_categories:
            assert category in CATEGORY_TO_FOLDER_MAP
            assert isinstance(CATEGORY_TO_FOLDER_MAP[category], str)
            assert len(CATEGORY_TO_FOLDER_MAP[category]) > 0

    def test_mapping_matches_gmail(self):
        """Test that IONOS mappings match Gmail for consistency."""
        from agent_platform.providers.gmail_handler import CATEGORY_TO_LABEL_MAP as GMAIL_MAP

        # Both should have same keys
        assert set(CATEGORY_TO_FOLDER_MAP.keys()) == set(GMAIL_MAP.keys())

        # Spam should be consistently 'SPAM' (not 'Spam')
        assert CATEGORY_TO_FOLDER_MAP['spam'] == 'SPAM'
        assert GMAIL_MAP['spam'] == 'SPAM'


class TestSingleFolderLimitation:
    """Test IMAP single-folder limitation."""

    @pytest.mark.asyncio
    async def test_only_primary_category_applied(self, ionos_handler):
        """Test that only primary category is used (IMAP limitation)."""
        mock_email = Mock()
        mock_email.email_id = 'msg_123'
        mock_email.ionos_folder_applied = None

        with patch.object(ionos_handler, '_create_folder_if_needed', new_callable=AsyncMock) as mock_create, \
             patch.object(ionos_handler, '_move_to_folder', new_callable=AsyncMock) as mock_move:

            mock_create.return_value = True
            mock_move.return_value = True

            result = await ionos_handler.apply_classification(
                email_record=mock_email,
                account_id='ionos_1',
                primary_category='wichtig_todo',
                secondary_categories=['termine', 'finanzen'],  # Should be ignored
                importance_score=0.85,
                confidence=0.90
            )

            # Only primary category should be applied
            assert result['success'] is True
            assert mock_email.ionos_folder_applied == CATEGORY_TO_FOLDER_MAP['wichtig_todo']
            assert result['folder_applied'] == CATEGORY_TO_FOLDER_MAP['wichtig_todo']

            # Secondary categories should be acknowledged but not applied
            assert result['secondary_ignored'] == ['termine', 'finanzen']

    @pytest.mark.asyncio
    async def test_secondary_categories_ignored(self, ionos_handler):
        """Test that secondary categories are explicitly ignored."""
        mock_email = Mock()
        mock_email.email_id = 'msg_123'
        mock_email.ionos_folder_applied = None

        with patch.object(ionos_handler, '_create_folder_if_needed', new_callable=AsyncMock), \
             patch.object(ionos_handler, '_move_to_folder', new_callable=AsyncMock):

            result = await ionos_handler.apply_classification(
                email_record=mock_email,
                account_id='ionos_1',
                primary_category='newsletter',
                secondary_categories=['werbung'],
                importance_score=0.30,
                confidence=0.85
            )

            # Result should explicitly mention ignored secondary categories
            assert 'secondary_ignored' in result
            assert result['secondary_ignored'] == ['werbung']

    @pytest.mark.asyncio
    async def test_empty_secondary_categories(self, ionos_handler):
        """Test handling of emails with only primary category."""
        mock_email = Mock()
        mock_email.email_id = 'msg_123'
        mock_email.ionos_folder_applied = None

        with patch.object(ionos_handler, '_create_folder_if_needed', new_callable=AsyncMock), \
             patch.object(ionos_handler, '_move_to_folder', new_callable=AsyncMock):

            result = await ionos_handler.apply_classification(
                email_record=mock_email,
                account_id='ionos_1',
                primary_category='spam',
                secondary_categories=[],  # No secondary
                importance_score=0.05,
                confidence=0.99
            )

            assert result['success'] is True
            assert result['secondary_ignored'] == []
            assert mock_email.ionos_folder_applied == 'SPAM'


class TestFolderOperations:
    """Test IMAP folder operations."""

    @pytest.mark.asyncio
    async def test_folder_created_if_not_exists(self, ionos_handler):
        """Test that folders are created if they don't exist."""
        with patch('agent_platform.providers.ionos_handler.get_imap_connection') as mock_imap:
            mock_conn = Mock()
            mock_imap.return_value.__enter__.return_value = mock_conn

            # Mock list() to return empty (folder doesn't exist)
            mock_conn.list.return_value = (None, [])

            # Mock create()
            mock_conn.create.return_value = (None, None)

            created = await ionos_handler._create_folder_if_needed(
                account_id='ionos_1',
                folder_name='NewFolder'
            )

            # Should create folder
            mock_conn.create.assert_called_once_with('NewFolder')
            assert created is True

    @pytest.mark.asyncio
    async def test_existing_folder_not_recreated(self, ionos_handler):
        """Test that existing folders are not recreated."""
        with patch('agent_platform.providers.ionos_handler.get_imap_connection') as mock_imap:
            mock_conn = Mock()
            mock_imap.return_value.__enter__.return_value = mock_conn

            # Mock list() to return existing folder
            mock_conn.list.return_value = (None, [b'() "/" ExistingFolder'])

            created = await ionos_handler._create_folder_if_needed(
                account_id='ionos_1',
                folder_name='ExistingFolder'
            )

            # Should NOT create folder
            mock_conn.create.assert_not_called()
            assert created is False

    @pytest.mark.asyncio
    async def test_email_moved_to_folder(self, ionos_handler):
        """Test that email is moved to correct folder."""
        mock_email = Mock()
        mock_email.email_id = 'msg_123'
        mock_email.ionos_folder_applied = None

        with patch.object(ionos_handler, '_create_folder_if_needed', new_callable=AsyncMock), \
             patch.object(ionos_handler, '_move_to_folder', new_callable=AsyncMock) as mock_move:

            mock_move.return_value = True

            result = await ionos_handler.apply_classification(
                email_record=mock_email,
                account_id='ionos_1',
                primary_category='finanzen',
                secondary_categories=[],
                importance_score=0.80,
                confidence=0.90
            )

            # Should move email
            assert result['moved'] is True
            mock_move.assert_called_once_with(
                account_id='ionos_1',
                email_id='msg_123',
                folder_name=CATEGORY_TO_FOLDER_MAP['finanzen']
            )


class TestProviderComparison:
    """Test that IONOS handler behaves consistently with Gmail."""

    @pytest.mark.asyncio
    async def test_same_categories_supported(self, ionos_handler):
        """Test that IONOS supports same categories as Gmail."""
        from agent_platform.providers.gmail_handler import CATEGORY_TO_LABEL_MAP as GMAIL_MAP

        # Both should support all 10 categories
        assert set(CATEGORY_TO_FOLDER_MAP.keys()) == set(GMAIL_MAP.keys())

    @pytest.mark.asyncio
    async def test_spam_handling_consistent(self, ionos_handler):
        """Test that spam is handled consistently across providers."""
        mock_email = Mock()
        mock_email.email_id = 'msg_123'
        mock_email.ionos_folder_applied = None

        with patch.object(ionos_handler, '_create_folder_if_needed', new_callable=AsyncMock), \
             patch.object(ionos_handler, '_move_to_folder', new_callable=AsyncMock):

            result = await ionos_handler.apply_classification(
                email_record=mock_email,
                account_id='ionos_1',
                primary_category='spam',
                secondary_categories=[],
                importance_score=0.05,
                confidence=0.99
            )

            # Should use 'SPAM' folder (consistent with Gmail)
            assert mock_email.ionos_folder_applied == 'SPAM'
            assert result['folder_applied'] == 'SPAM'

    @pytest.mark.asyncio
    async def test_importance_scoring_consistent(self, ionos_handler):
        """Test that importance scores are handled consistently."""
        mock_email = Mock()
        mock_email.email_id = 'msg_123'
        mock_email.ionos_folder_applied = None

        with patch.object(ionos_handler, '_create_folder_if_needed', new_callable=AsyncMock), \
             patch.object(ionos_handler, '_move_to_folder', new_callable=AsyncMock):

            # High importance
            result_high = await ionos_handler.apply_classification(
                email_record=mock_email,
                account_id='ionos_1',
                primary_category='wichtig_todo',
                secondary_categories=[],
                importance_score=0.95,
                confidence=0.95
            )

            # Low importance
            result_low = await ionos_handler.apply_classification(
                email_record=mock_email,
                account_id='ionos_1',
                primary_category='newsletter',
                secondary_categories=[],
                importance_score=0.20,
                confidence=0.85
            )

            # Both should succeed
            assert result_high['success'] is True
            assert result_low['success'] is True
