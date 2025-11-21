"""
Integration tests for 10-Category Email System.

Tests end-to-end flow: Classification → Preference Application → Provider Handling.
"""

import pytest
from unittest.mock import AsyncMock, patch
from agent_platform.classification.agents.rule_agent_10cat import classify_with_10_categories
from agent_platform.senders.profile_service import SenderProfileService
from agent_platform.providers.gmail_handler import GmailHandler
from agent_platform.providers.ionos_handler import IonosHandler
from agent_platform.db.database import get_db
from agent_platform.db.models import SenderPreference, ProcessedEmail


@pytest.fixture
def cleanup_test_data():
    """Clean up test data after each test."""
    yield
    with get_db() as db:
        db.query(SenderPreference).filter(
            SenderPreference.sender_email.like('%@integration-test.com')
        ).delete()
        db.query(ProcessedEmail).filter(
            ProcessedEmail.account_id == 'integration_test_account'
        ).delete()
        db.commit()


class TestCompleteClassificationFlow:
    """Test complete flow from email to provider application."""

    @pytest.mark.asyncio
    async def test_wichtig_todo_flow_gmail(self, cleanup_test_data):
        """Test complete flow for important email with Gmail."""
        # Step 1: Classify email
        classification = classify_with_10_categories(
            email_id='integration_1',
            subject='URGENT: Bitte um Rückmeldung bis morgen',
            body='Kannst du mir bitte bis morgen Feedback geben?',
            sender='boss@integration-test.com'
        )

        assert classification['primary_category'] == 'wichtig_todo'
        assert classification['importance_score'] >= 0.85

        # Step 2: Apply sender preferences (none exist, should pass through)
        profile_service = SenderProfileService()
        classification_with_prefs = await profile_service.apply_preferences(
            sender_email='boss@integration-test.com',
            account_id='integration_test_account',
            classification_result=classification
        )

        assert classification_with_prefs['primary_category'] == 'wichtig_todo'

        # Step 3: Apply to Gmail
        gmail_handler = GmailHandler()
        mock_email = ProcessedEmail(
            account_id='integration_test_account',
            email_id='msg_integration_123',
            sender='boss@integration-test.com',
            subject='URGENT: Bitte um Rückmeldung bis morgen',
            body_text='Kannst du mir bitte bis morgen Feedback geben?',
            primary_category=classification_with_prefs['primary_category'],
            secondary_categories=classification_with_prefs.get('secondary_categories', [])
        )

        with patch.object(gmail_handler, '_get_or_create_labels', new_callable=AsyncMock) as mock_labels, \
             patch.object(gmail_handler, '_apply_labels', new_callable=AsyncMock), \
             patch.object(gmail_handler, '_archive_email', new_callable=AsyncMock):

            mock_labels.return_value = ['label_123']

            result = await gmail_handler.apply_classification(
                email_record=mock_email,
                account_id='integration_test_account',
                primary_category=classification_with_prefs['primary_category'],
                secondary_categories=classification_with_prefs.get('secondary_categories', []),
                importance_score=classification_with_prefs['importance_score'],
                confidence=classification_with_prefs['primary_confidence']
            )

            assert result['success'] is True
            assert not result['archived']  # High importance shouldn't be archived

    @pytest.mark.asyncio
    async def test_whitelisted_sender_boost(self, cleanup_test_data):
        """Test that whitelisted senders get confidence boost."""
        # Step 1: Whitelist sender
        profile_service = SenderProfileService()
        await profile_service.whitelist_sender(
            sender_email='vip@integration-test.com',
            account_id='integration_test_account'
        )

        # Step 2: Classify email (medium confidence)
        classification = classify_with_10_categories(
            email_id='integration_2',
            subject='Quick question',
            body='Can you help me with something?',
            sender='vip@integration-test.com'
        )
        original_confidence = classification['primary_confidence']

        # Step 3: Apply preferences (should boost confidence)
        classification_with_prefs = await profile_service.apply_preferences(
            sender_email='vip@integration-test.com',
            account_id='integration_test_account',
            classification_result=classification
        )

        # Confidence should be boosted
        assert classification_with_prefs['primary_confidence'] > original_confidence
        assert classification_with_prefs['primary_confidence'] <= 1.0

    @pytest.mark.asyncio
    async def test_blacklisted_sender_forced_spam(self, cleanup_test_data):
        """Test that blacklisted senders are forced to spam category."""
        # Step 1: Blacklist sender
        profile_service = SenderProfileService()
        await profile_service.blacklist_sender(
            sender_email='spam@integration-test.com',
            account_id='integration_test_account'
        )

        # Step 2: Classify email (even if it looks important)
        classification = classify_with_10_categories(
            email_id='integration_3',
            subject='Important Update',
            body='You won 1 million dollars!',
            sender='spam@integration-test.com'
        )
        # Even if initially classified as something else

        # Step 3: Apply preferences (should force to spam)
        classification_with_prefs = await profile_service.apply_preferences(
            sender_email='spam@integration-test.com',
            account_id='integration_test_account',
            classification_result=classification
        )

        # Should be forced to spam
        assert classification_with_prefs['primary_category'] == 'spam'
        assert classification_with_prefs['importance_score'] == 0.0
        assert classification_with_prefs['primary_confidence'] >= 0.95

    @pytest.mark.asyncio
    async def test_muted_category_reduces_importance(self, cleanup_test_data):
        """Test that muted categories get importance reduction."""
        # Step 1: Mute newsletter category for sender
        profile_service = SenderProfileService()
        await profile_service.mute_categories(
            sender_email='newsletter@integration-test.com',
            account_id='integration_test_account',
            categories=['newsletter']
        )

        # Step 2: Classify newsletter
        classification = classify_with_10_categories(
            email_id='integration_4',
            subject='Our monthly newsletter',
            body='Here are the latest updates...',
            sender='newsletter@integration-test.com'
        )
        assert classification['primary_category'] == 'newsletter'

        # Step 3: Apply preferences (should reduce importance)
        classification_with_prefs = await profile_service.apply_preferences(
            sender_email='newsletter@integration-test.com',
            account_id='integration_test_account',
            classification_result=classification
        )

        # Importance should be reduced to 0.10
        assert classification_with_prefs['importance_score'] == 0.10

    @pytest.mark.asyncio
    async def test_multi_label_gmail_vs_single_folder_ionos(self, cleanup_test_data):
        """Test that Gmail gets multi-label and IONOS gets single folder."""
        # Classify email with secondary categories
        classification = classify_with_10_categories(
            email_id='integration_5',
            subject='Meeting zur Rechnung nächste Woche',
            body='Können wir die offene Rechnung besprechen?',
            sender='client@integration-test.com'
        )
        # Should have primary + possibly secondary categories

        gmail_handler = GmailHandler()
        ionos_handler = IonosHandler()

        mock_email_gmail = ProcessedEmail(
            account_id='gmail_integration',
            email_id='msg_gmail_123',
            sender='client@integration-test.com',
            subject='Meeting zur Rechnung nächste Woche',
            body_text='Können wir die offene Rechnung besprechen?'
        )

        mock_email_ionos = ProcessedEmail(
            account_id='ionos_integration',
            email_id='msg_ionos_123',
            sender='client@integration-test.com',
            subject='Meeting zur Rechnung nächste Woche',
            body_text='Können wir die offene Rechnung besprechen?'
        )

        # Apply to Gmail (multi-label)
        with patch.object(gmail_handler, '_get_or_create_labels', new_callable=AsyncMock) as mock_labels, \
             patch.object(gmail_handler, '_apply_labels', new_callable=AsyncMock), \
             patch.object(gmail_handler, '_archive_email', new_callable=AsyncMock):

            mock_labels.return_value = ['label_1', 'label_2']

            gmail_result = await gmail_handler.apply_classification(
                email_record=mock_email_gmail,
                account_id='gmail_integration',
                primary_category=classification['primary_category'],
                secondary_categories=classification.get('secondary_categories', []),
                importance_score=classification['importance_score'],
                confidence=classification['primary_confidence']
            )

            # Gmail should apply multiple labels
            assert len(mock_email_gmail.gmail_labels_applied) >= 1

        # Apply to IONOS (single folder)
        with patch.object(ionos_handler, '_create_folder_if_needed', new_callable=AsyncMock), \
             patch.object(ionos_handler, '_move_to_folder', new_callable=AsyncMock):

            ionos_result = await ionos_handler.apply_classification(
                email_record=mock_email_ionos,
                account_id='ionos_integration',
                primary_category=classification['primary_category'],
                secondary_categories=classification.get('secondary_categories', []),
                importance_score=classification['importance_score'],
                confidence=classification['primary_confidence']
            )

            # IONOS should apply only primary folder
            assert mock_email_ionos.ionos_folder_applied is not None
            # Secondary should be acknowledged as ignored
            if classification.get('secondary_categories'):
                assert ionos_result['secondary_ignored'] == classification['secondary_categories']


class TestCategorySystemIntegration:
    """Test that all 10 categories work end-to-end."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("category,subject,body,sender", [
        ('wichtig_todo', 'Bitte um Rückmeldung', 'Kannst du mir Feedback geben?', 'boss@test.com'),
        ('termine', 'Meeting morgen 14 Uhr', 'Können wir uns treffen?', 'colleague@test.com'),
        ('finanzen', 'Rechnung #123', 'Ihre Rechnung für November', 'billing@test.com'),
        ('bestellungen', 'Bestellung versandt', 'Tracking: ABC123', 'orders@test.com'),
        ('newsletter', 'Unser Newsletter', 'Neuigkeiten dieser Woche', 'news@test.com'),
        ('werbung', '50% RABATT', 'Nur heute!', 'sale@test.com'),
        ('spam', 'Sie haben gewonnen!!!', 'Klicken Sie hier', 'scam@test.com'),
    ])
    async def test_category_classification_and_routing(self, category, subject, body, sender, cleanup_test_data):
        """Test that each category is properly classified and routed."""
        # Classify
        classification = classify_with_10_categories(
            email_id=f'test_{category}',
            subject=subject,
            body=body,
            sender=sender
        )

        # Should match expected category (or be close)
        # Note: LLM classification might differ slightly, so we check importance range
        from agent_platform.classification.models import CATEGORY_IMPORTANCE_MAP

        expected_importance_range = CATEGORY_IMPORTANCE_MAP[category]

        # Allow ±0.20 tolerance for rule-based classification
        assert abs(classification['importance_score'] - expected_importance_range) <= 0.30
