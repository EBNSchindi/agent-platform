"""
Unit tests for Gmail Handler.

Tests Gmail-specific multi-label operations.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from agent_platform.providers.gmail_handler import GmailHandler, CATEGORY_TO_LABEL_MAP


@pytest.fixture
def gmail_handler():
    """Create GmailHandler instance."""
    return GmailHandler()


class TestCategoryMapping:
    """Test category to Gmail label mapping."""

    def test_all_categories_mapped(self):
        """Test that all 10 categories have label mappings."""
        expected_categories = [
            'wichtig_todo', 'termine', 'finanzen', 'bestellungen',
            'job_projekte', 'vertraege', 'persoenlich', 'newsletter',
            'werbung', 'spam'
        ]

        for category in expected_categories:
            assert category in CATEGORY_TO_LABEL_MAP
            assert isinstance(CATEGORY_TO_LABEL_MAP[category], str)
            assert len(CATEGORY_TO_LABEL_MAP[category]) > 0

    def test_label_names_descriptive(self):
        """Test that label names are descriptive."""
        # Labels should be human-readable
        assert 'Important' in CATEGORY_TO_LABEL_MAP['wichtig_todo']
        assert 'Events' in CATEGORY_TO_LABEL_MAP['termine'] or 'Appointments' in CATEGORY_TO_LABEL_MAP['termine']
        assert 'Finance' in CATEGORY_TO_LABEL_MAP['finanzen'] or 'Invoices' in CATEGORY_TO_LABEL_MAP['finanzen']
        assert 'SPAM' in CATEGORY_TO_LABEL_MAP['spam']


class TestMultiLabelSupport:
    """Test Gmail multi-label functionality."""

    @pytest.mark.asyncio
    async def test_primary_and_secondary_labels_applied(self, gmail_handler):
        """Test that both primary and secondary categories become labels."""
        mock_email = Mock()
        mock_email.email_id = 'msg_123'
        mock_email.gmail_labels_applied = []

        with patch.object(gmail_handler, '_get_or_create_labels', new_callable=AsyncMock) as mock_get_labels, \
             patch.object(gmail_handler, '_apply_labels', new_callable=AsyncMock) as mock_apply_labels:

            mock_get_labels.return_value = ['label_1', 'label_2', 'label_3']
            mock_apply_labels.return_value = True

            result = await gmail_handler.apply_classification(
                email_record=mock_email,
                account_id='gmail_1',
                primary_category='wichtig_todo',
                secondary_categories=['termine', 'finanzen'],
                importance_score=0.85,
                confidence=0.90
            )

            # Should apply all 3 labels (1 primary + 2 secondary)
            assert result['success'] is True
            assert len(mock_email.gmail_labels_applied) == 3
            assert 'Important/ToDo' in mock_email.gmail_labels_applied
            # Note: Exact label names depend on CATEGORY_TO_LABEL_MAP

    @pytest.mark.asyncio
    async def test_max_labels_limit(self, gmail_handler):
        """Test handling of maximum labels (primary + 3 secondary)."""
        mock_email = Mock()
        mock_email.email_id = 'msg_123'
        mock_email.gmail_labels_applied = []

        with patch.object(gmail_handler, '_get_or_create_labels', new_callable=AsyncMock) as mock_get_labels, \
             patch.object(gmail_handler, '_apply_labels', new_callable=AsyncMock):

            mock_get_labels.return_value = ['label_1', 'label_2', 'label_3', 'label_4']

            result = await gmail_handler.apply_classification(
                email_record=mock_email,
                account_id='gmail_1',
                primary_category='wichtig_todo',
                secondary_categories=['termine', 'finanzen', 'job_projekte'],  # Max 3 secondary
                importance_score=0.85,
                confidence=0.90
            )

            # Should apply max 4 labels (1 primary + 3 secondary)
            assert result['success'] is True
            assert len(mock_email.gmail_labels_applied) <= 4

    @pytest.mark.asyncio
    async def test_empty_secondary_categories(self, gmail_handler):
        """Test handling of emails with only primary category."""
        mock_email = Mock()
        mock_email.email_id = 'msg_123'
        mock_email.gmail_labels_applied = []

        with patch.object(gmail_handler, '_get_or_create_labels', new_callable=AsyncMock) as mock_get_labels, \
             patch.object(gmail_handler, '_apply_labels', new_callable=AsyncMock):

            mock_get_labels.return_value = ['label_1']

            result = await gmail_handler.apply_classification(
                email_record=mock_email,
                account_id='gmail_1',
                primary_category='newsletter',
                secondary_categories=[],  # No secondary
                importance_score=0.30,
                confidence=0.85
            )

            # Should apply only 1 label (primary)
            assert result['success'] is True
            assert len(mock_email.gmail_labels_applied) == 1


class TestImportanceBasedActions:
    """Test importance-based automatic actions."""

    @pytest.mark.asyncio
    async def test_low_importance_gets_archived(self, gmail_handler):
        """Test that low-importance emails are archived."""
        mock_email = Mock()
        mock_email.email_id = 'msg_123'
        mock_email.gmail_labels_applied = []

        with patch.object(gmail_handler, '_get_or_create_labels', new_callable=AsyncMock), \
             patch.object(gmail_handler, '_apply_labels', new_callable=AsyncMock), \
             patch.object(gmail_handler, '_archive_email', new_callable=AsyncMock) as mock_archive:

            mock_archive.return_value = True

            result = await gmail_handler.apply_classification(
                email_record=mock_email,
                account_id='gmail_1',
                primary_category='newsletter',
                secondary_categories=[],
                importance_score=0.25,  # Low importance
                confidence=0.90
            )

            # Should be archived
            assert result['archived'] is True
            mock_archive.assert_called_once()

    @pytest.mark.asyncio
    async def test_high_importance_not_archived(self, gmail_handler):
        """Test that high-importance emails are NOT archived."""
        mock_email = Mock()
        mock_email.email_id = 'msg_123'
        mock_email.gmail_labels_applied = []

        with patch.object(gmail_handler, '_get_or_create_labels', new_callable=AsyncMock), \
             patch.object(gmail_handler, '_apply_labels', new_callable=AsyncMock), \
             patch.object(gmail_handler, '_archive_email', new_callable=AsyncMock) as mock_archive:

            mock_archive.return_value = False

            result = await gmail_handler.apply_classification(
                email_record=mock_email,
                account_id='gmail_1',
                primary_category='wichtig_todo',
                secondary_categories=[],
                importance_score=0.90,  # High importance
                confidence=0.95
            )

            # Should NOT be archived
            assert result['archived'] is False

    @pytest.mark.asyncio
    async def test_spam_gets_marked(self, gmail_handler):
        """Test that spam emails get SPAM label."""
        mock_email = Mock()
        mock_email.email_id = 'msg_123'
        mock_email.gmail_labels_applied = []

        with patch.object(gmail_handler, '_get_or_create_labels', new_callable=AsyncMock) as mock_get_labels, \
             patch.object(gmail_handler, '_apply_labels', new_callable=AsyncMock):

            mock_get_labels.return_value = ['SPAM']

            result = await gmail_handler.apply_classification(
                email_record=mock_email,
                account_id='gmail_1',
                primary_category='spam',
                secondary_categories=[],
                importance_score=0.05,
                confidence=0.99
            )

            assert result['success'] is True
            assert 'SPAM' in mock_email.gmail_labels_applied


class TestLabelCreation:
    """Test Gmail label creation and management."""

    @pytest.mark.asyncio
    async def test_label_created_if_not_exists(self, gmail_handler):
        """Test that labels are created if they don't exist."""
        with patch('agent_platform.providers.gmail_handler.get_gmail_service') as mock_service:
            mock_labels = Mock()
            mock_service.return_value.users.return_value.labels.return_value = mock_labels

            # Mock list() to return empty (label doesn't exist)
            mock_labels.list.return_value.execute.return_value = {'labels': []}

            # Mock create()
            mock_labels.create.return_value.execute.return_value = {'id': 'new_label_123'}

            label_ids = await gmail_handler._get_or_create_labels(
                account_id='gmail_1',
                label_names=['NewLabel']
            )

            # Should create label
            mock_labels.create.assert_called_once()
            assert 'new_label_123' in label_ids

    @pytest.mark.asyncio
    async def test_existing_label_reused(self, gmail_handler):
        """Test that existing labels are reused."""
        with patch('agent_platform.providers.gmail_handler.get_gmail_service') as mock_service:
            mock_labels = Mock()
            mock_service.return_value.users.return_value.labels.return_value = mock_labels

            # Mock list() to return existing label
            mock_labels.list.return_value.execute.return_value = {
                'labels': [{'id': 'existing_123', 'name': 'ExistingLabel'}]
            }

            label_ids = await gmail_handler._get_or_create_labels(
                account_id='gmail_1',
                label_names=['ExistingLabel']
            )

            # Should NOT create label, just reuse
            mock_labels.create.assert_not_called()
            assert 'existing_123' in label_ids
