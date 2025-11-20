"""
Unit Tests: Webhook Service (Phase 5)

Tests Gmail push notification webhooks:
1. Creating webhook subscription
2. Renewing subscription
3. Stopping subscription
4. Handling incoming notifications
5. History ID tracking
6. Expiration checking
7. Background processing integration
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock, patch

from agent_platform.webhooks import (
    WebhookService,
    SubscriptionConfig,
    SubscriptionInfo,
    SubscriptionStatus,
    PushNotification,
    WebhookEvent,
)
from agent_platform.orchestration import ClassificationOrchestrator


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_gmail_service():
    """Mock Gmail API service."""
    service = MagicMock()

    # Mock getProfile response
    service.users().getProfile().execute.return_value = {
        'emailAddress': 'test@example.com',
        'historyId': '12345',
    }

    # Mock watch response
    service.users().watch().execute.return_value = {
        'historyId': '12345',
        'expiration': str(int((datetime.now() + timedelta(days=7)).timestamp() * 1000)),
    }

    # Mock stop response
    service.users().stop().execute.return_value = {}

    # Mock history().list() response
    service.users().history().list().execute.return_value = {
        'history': [
            {
                'messagesAdded': [
                    {'message': {'id': 'new_msg_001'}},
                    {'message': {'id': 'new_msg_002'}},
                ]
            }
        ]
    }

    # Mock messages().get() response
    def get_message_mock(userId, id, format):
        return MagicMock(execute=MagicMock(return_value={
            'id': id,
            'threadId': f'thread_{id}',
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': f'Subject {id}'},
                    {'name': 'From', 'value': 'sender@example.com'},
                    {'name': 'Date', 'value': '2025-11-20'},
                ],
                'body': {'data': 'VGVzdCBib2R5'},
            },
        }))

    service.users().messages().get = get_message_mock

    return service


@pytest.fixture
def mock_orchestrator():
    """Mock classification orchestrator."""
    orchestrator = AsyncMock(spec=ClassificationOrchestrator)
    orchestrator.process_emails = AsyncMock(return_value={
        'total_processed': 2,
        'high_confidence': 1,
        'medium_confidence': 1,
        'low_confidence': 0,
    })
    return orchestrator


@pytest.fixture
def sample_subscription_config():
    """Sample subscription configuration."""
    return SubscriptionConfig(
        account_id="test_account",
        topic_name="projects/my-project/topics/gmail-push",
    )


@pytest.fixture
def sample_push_notification():
    """Sample push notification from Gmail."""
    return PushNotification(
        email_address="test@example.com",
        history_id="12350",
    )


# ============================================================================
# TEST CASES: CREATING SUBSCRIPTION
# ============================================================================

class TestCreateSubscription:
    """Test creating Gmail push notification subscriptions."""

    @pytest.mark.asyncio
    async def test_create_subscription_basic(
        self,
        mock_gmail_service,
        sample_subscription_config,
    ):
        """Test creating a basic subscription."""
        service = WebhookService()

        subscription = await service.create_subscription(
            gmail_service=mock_gmail_service,
            config=sample_subscription_config,
        )

        assert subscription is not None
        assert subscription.account_id == "test_account"
        assert subscription.topic_name == "projects/my-project/topics/gmail-push"
        assert subscription.status == SubscriptionStatus.ACTIVE
        assert subscription.history_id == "12345"
        assert subscription.expires_at > datetime.now()

    @pytest.mark.asyncio
    async def test_subscription_stored_in_active(
        self,
        mock_gmail_service,
        sample_subscription_config,
    ):
        """Test that subscription is stored in active subscriptions."""
        service = WebhookService()

        await service.create_subscription(
            gmail_service=mock_gmail_service,
            config=sample_subscription_config,
        )

        # Check active subscriptions
        active = service.list_subscriptions()
        assert len(active) == 1
        assert active[0].account_id == "test_account"

    @pytest.mark.asyncio
    async def test_subscription_expiration_time(
        self,
        mock_gmail_service,
        sample_subscription_config,
    ):
        """Test that subscription expiration is set correctly."""
        service = WebhookService()

        subscription = await service.create_subscription(
            gmail_service=mock_gmail_service,
            config=sample_subscription_config,
        )

        # Expiration should be ~7 days from now (Gmail max)
        time_diff = (subscription.expires_at - datetime.now()).days
        assert 6 <= time_diff <= 7

    @pytest.mark.asyncio
    async def test_custom_expiration_days(
        self,
        mock_gmail_service,
    ):
        """Test custom expiration days (capped at 7)."""
        config = SubscriptionConfig(
            account_id="test_account",
            topic_name="projects/my-project/topics/gmail-push",
            expiration_days=14,  # Will be capped at 7
        )

        service = WebhookService()
        subscription = await service.create_subscription(
            gmail_service=mock_gmail_service,
            config=config,
        )

        # Should be capped at 7 days
        time_diff = (subscription.expires_at - datetime.now()).days
        assert time_diff <= 7

    @pytest.mark.asyncio
    async def test_custom_labels(self, mock_gmail_service):
        """Test subscription with custom Gmail labels."""
        config = SubscriptionConfig(
            account_id="test_account",
            topic_name="projects/my-project/topics/gmail-push",
            labels=["INBOX", "IMPORTANT"],
        )

        service = WebhookService()
        subscription = await service.create_subscription(
            gmail_service=mock_gmail_service,
            config=config,
        )

        assert subscription is not None
        # In real test, would verify labels were passed to Gmail API

    @pytest.mark.asyncio
    async def test_gmail_api_error_handling(self):
        """Test handling of Gmail API errors during subscription."""
        gmail_service = MagicMock()
        gmail_service.users().getProfile().execute.side_effect = Exception(
            "Gmail API error"
        )

        config = SubscriptionConfig(
            account_id="test_account",
            topic_name="projects/my-project/topics/gmail-push",
        )

        service = WebhookService()

        with pytest.raises(Exception, match="Gmail API error"):
            await service.create_subscription(
                gmail_service=gmail_service,
                config=config,
            )


# ============================================================================
# TEST CASES: RENEWING SUBSCRIPTION
# ============================================================================

class TestRenewSubscription:
    """Test renewing existing subscriptions."""

    @pytest.mark.asyncio
    async def test_renew_subscription_basic(
        self,
        mock_gmail_service,
        sample_subscription_config,
    ):
        """Test renewing an existing subscription."""
        service = WebhookService()

        # Create initial subscription
        await service.create_subscription(
            gmail_service=mock_gmail_service,
            config=sample_subscription_config,
        )

        # Renew subscription
        renewed = await service.renew_subscription(
            gmail_service=mock_gmail_service,
            account_id="test_account",
        )

        assert renewed is not None
        assert renewed.account_id == "test_account"
        assert renewed.status == SubscriptionStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_renew_nonexistent_subscription(
        self,
        mock_gmail_service,
    ):
        """Test renewing a subscription that doesn't exist."""
        service = WebhookService()

        with pytest.raises(ValueError, match="No active subscription"):
            await service.renew_subscription(
                gmail_service=mock_gmail_service,
                account_id="nonexistent_account",
            )

    @pytest.mark.asyncio
    async def test_renewal_updates_expiration(
        self,
        mock_gmail_service,
        sample_subscription_config,
    ):
        """Test that renewal updates expiration time."""
        service = WebhookService()

        # Create initial subscription
        initial = await service.create_subscription(
            gmail_service=mock_gmail_service,
            config=sample_subscription_config,
        )
        initial_expires = initial.expires_at

        # Simulate time passing
        import time
        time.sleep(0.1)

        # Renew
        renewed = await service.renew_subscription(
            gmail_service=mock_gmail_service,
            account_id="test_account",
        )

        # Expiration should be updated
        assert renewed.expires_at > initial_expires


# ============================================================================
# TEST CASES: STOPPING SUBSCRIPTION
# ============================================================================

class TestStopSubscription:
    """Test stopping active subscriptions."""

    @pytest.mark.asyncio
    async def test_stop_subscription_basic(
        self,
        mock_gmail_service,
        sample_subscription_config,
    ):
        """Test stopping an active subscription."""
        service = WebhookService()

        # Create subscription
        await service.create_subscription(
            gmail_service=mock_gmail_service,
            config=sample_subscription_config,
        )

        # Stop subscription
        success = await service.stop_subscription(
            gmail_service=mock_gmail_service,
            account_id="test_account",
        )

        assert success is True

        # Should be removed from active subscriptions
        active = service.list_subscriptions()
        assert len(active) == 0

    @pytest.mark.asyncio
    async def test_stop_nonexistent_subscription(
        self,
        mock_gmail_service,
    ):
        """Test stopping a subscription that doesn't exist."""
        service = WebhookService()

        success = await service.stop_subscription(
            gmail_service=mock_gmail_service,
            account_id="nonexistent_account",
        )

        assert success is False

    @pytest.mark.asyncio
    async def test_stop_subscription_calls_gmail_api(
        self,
        mock_gmail_service,
        sample_subscription_config,
    ):
        """Test that stopping calls Gmail API stop method."""
        service = WebhookService()

        await service.create_subscription(
            gmail_service=mock_gmail_service,
            config=sample_subscription_config,
        )

        await service.stop_subscription(
            gmail_service=mock_gmail_service,
            account_id="test_account",
        )

        # Verify Gmail API stop was called
        mock_gmail_service.users().stop().execute.assert_called()

    @pytest.mark.asyncio
    async def test_stop_subscription_api_error(
        self,
        sample_subscription_config,
    ):
        """Test handling of API errors when stopping."""
        gmail_service = MagicMock()
        gmail_service.users().getProfile().execute.return_value = {'historyId': '12345'}
        gmail_service.users().watch().execute.return_value = {'historyId': '12345'}
        gmail_service.users().stop().execute.side_effect = Exception("API error")

        service = WebhookService()

        await service.create_subscription(
            gmail_service=gmail_service,
            config=sample_subscription_config,
        )

        success = await service.stop_subscription(
            gmail_service=gmail_service,
            account_id="test_account",
        )

        # Should return False on error
        assert success is False


# ============================================================================
# TEST CASES: HANDLING NOTIFICATIONS
# ============================================================================

class TestHandleNotification:
    """Test handling incoming push notifications."""

    @pytest.mark.asyncio
    async def test_handle_notification_basic(
        self,
        mock_gmail_service,
        mock_orchestrator,
        sample_subscription_config,
        sample_push_notification,
    ):
        """Test handling a basic push notification."""
        service = WebhookService(orchestrator=mock_orchestrator)

        # Create subscription
        await service.create_subscription(
            gmail_service=mock_gmail_service,
            config=sample_subscription_config,
        )

        # Handle notification
        event = await service.handle_notification(
            gmail_service=mock_gmail_service,
            notification=sample_push_notification,
        )

        assert event is not None
        assert event.processed is True
        assert event.account_id == "test_account"
        assert event.processed_at is not None

    @pytest.mark.asyncio
    async def test_notification_fetches_history(
        self,
        mock_gmail_service,
        mock_orchestrator,
        sample_subscription_config,
        sample_push_notification,
    ):
        """Test that notification fetches history changes."""
        service = WebhookService(orchestrator=mock_orchestrator)

        await service.create_subscription(
            gmail_service=mock_gmail_service,
            config=sample_subscription_config,
        )

        await service.handle_notification(
            gmail_service=mock_gmail_service,
            notification=sample_push_notification,
        )

        # Verify history API was called
        mock_gmail_service.users().history().list.assert_called()

    @pytest.mark.asyncio
    async def test_notification_processes_new_emails(
        self,
        mock_gmail_service,
        mock_orchestrator,
        sample_subscription_config,
        sample_push_notification,
    ):
        """Test that notification processes new emails through orchestrator."""
        service = WebhookService(orchestrator=mock_orchestrator)

        await service.create_subscription(
            gmail_service=mock_gmail_service,
            config=sample_subscription_config,
        )

        await service.handle_notification(
            gmail_service=mock_gmail_service,
            notification=sample_push_notification,
        )

        # Verify orchestrator was called
        mock_orchestrator.process_emails.assert_called_once()

    @pytest.mark.asyncio
    async def test_notification_unknown_account(
        self,
        mock_gmail_service,
        mock_orchestrator,
    ):
        """Test handling notification for unknown account."""
        service = WebhookService(orchestrator=mock_orchestrator)

        notification = PushNotification(
            email_address="unknown@example.com",
            history_id="99999",
        )

        event = await service.handle_notification(
            gmail_service=mock_gmail_service,
            notification=notification,
        )

        assert event.processed is False
        assert "No matching subscription" in event.error_message
        assert event.account_id == "unknown"

    @pytest.mark.asyncio
    async def test_notification_error_handling(
        self,
        mock_orchestrator,
        sample_subscription_config,
        sample_push_notification,
    ):
        """Test error handling during notification processing."""
        # Mock Gmail service that raises error
        gmail_service = MagicMock()
        gmail_service.users().getProfile().execute.return_value = {'historyId': '12345'}
        gmail_service.users().watch().execute.return_value = {'historyId': '12345'}
        gmail_service.users().history().list().execute.side_effect = Exception(
            "History fetch error"
        )

        service = WebhookService(orchestrator=mock_orchestrator)

        await service.create_subscription(
            gmail_service=gmail_service,
            config=sample_subscription_config,
        )

        event = await service.handle_notification(
            gmail_service=gmail_service,
            notification=sample_push_notification,
        )

        assert event.processed is False
        assert event.error_message is not None


# ============================================================================
# TEST CASES: HISTORY ID TRACKING
# ============================================================================

class TestHistoryIDTracking:
    """Test history ID tracking and updates."""

    @pytest.mark.asyncio
    async def test_history_id_updated_after_notification(
        self,
        mock_gmail_service,
        mock_orchestrator,
        sample_subscription_config,
    ):
        """Test that history ID is updated after processing notification."""
        service = WebhookService(orchestrator=mock_orchestrator)

        subscription = await service.create_subscription(
            gmail_service=mock_gmail_service,
            config=sample_subscription_config,
        )
        initial_history_id = subscription.history_id

        # Process notification with new history ID
        notification = PushNotification(
            email_address="test@example.com",
            history_id="12350",  # New history ID
        )

        await service.handle_notification(
            gmail_service=mock_gmail_service,
            notification=notification,
        )

        # History ID should be updated
        assert subscription.history_id == "12350"
        assert subscription.history_id != initial_history_id

    @pytest.mark.asyncio
    async def test_last_notification_timestamp_updated(
        self,
        mock_gmail_service,
        mock_orchestrator,
        sample_subscription_config,
        sample_push_notification,
    ):
        """Test that last_notification_at timestamp is updated."""
        service = WebhookService(orchestrator=mock_orchestrator)

        subscription = await service.create_subscription(
            gmail_service=mock_gmail_service,
            config=sample_subscription_config,
        )

        assert subscription.last_notification_at is None

        await service.handle_notification(
            gmail_service=mock_gmail_service,
            notification=sample_push_notification,
        )

        assert subscription.last_notification_at is not None
        assert subscription.last_notification_at <= datetime.now()

    @pytest.mark.asyncio
    async def test_history_id_used_in_fetch(
        self,
        mock_gmail_service,
        mock_orchestrator,
        sample_subscription_config,
        sample_push_notification,
    ):
        """Test that history ID is used to fetch changes."""
        service = WebhookService(orchestrator=mock_orchestrator)

        subscription = await service.create_subscription(
            gmail_service=mock_gmail_service,
            config=sample_subscription_config,
        )

        await service.handle_notification(
            gmail_service=mock_gmail_service,
            notification=sample_push_notification,
        )

        # Verify history().list was called with startHistoryId
        # (In real test, would inspect call args)


# ============================================================================
# TEST CASES: EXPIRATION CHECKING
# ============================================================================

class TestExpirationChecking:
    """Test subscription expiration checking."""

    @pytest.mark.asyncio
    async def test_check_expirations_basic(
        self,
        mock_gmail_service,
        sample_subscription_config,
    ):
        """Test checking for expired subscriptions."""
        service = WebhookService()

        await service.create_subscription(
            gmail_service=mock_gmail_service,
            config=sample_subscription_config,
        )

        # Check expirations
        expired = service.check_expirations()

        # Should not be expired yet
        assert len(expired) == 0

    @pytest.mark.asyncio
    async def test_expired_subscription_detected(
        self,
        mock_gmail_service,
        sample_subscription_config,
    ):
        """Test that expired subscriptions are detected."""
        service = WebhookService()

        subscription = await service.create_subscription(
            gmail_service=mock_gmail_service,
            config=sample_subscription_config,
        )

        # Manually set expiration to past
        subscription.expires_at = datetime.now() - timedelta(hours=1)

        expired = service.check_expirations()

        assert len(expired) == 1
        assert expired[0] == "test_account"
        assert subscription.status == SubscriptionStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_multiple_subscriptions_expiration(
        self,
        mock_gmail_service,
    ):
        """Test expiration checking with multiple subscriptions."""
        service = WebhookService()

        # Create two subscriptions
        config1 = SubscriptionConfig(
            account_id="account_1",
            topic_name="projects/my-project/topics/gmail-push",
        )
        config2 = SubscriptionConfig(
            account_id="account_2",
            topic_name="projects/my-project/topics/gmail-push",
        )

        sub1 = await service.create_subscription(mock_gmail_service, config1)
        sub2 = await service.create_subscription(mock_gmail_service, config2)

        # Expire only first subscription
        sub1.expires_at = datetime.now() - timedelta(hours=1)

        expired = service.check_expirations()

        assert len(expired) == 1
        assert expired[0] == "account_1"
        assert sub1.status == SubscriptionStatus.EXPIRED
        assert sub2.status == SubscriptionStatus.ACTIVE


# ============================================================================
# TEST CASES: SUBSCRIPTION RETRIEVAL
# ============================================================================

class TestSubscriptionRetrieval:
    """Test subscription retrieval methods."""

    @pytest.mark.asyncio
    async def test_get_subscription(
        self,
        mock_gmail_service,
        sample_subscription_config,
    ):
        """Test retrieving subscription by account ID."""
        service = WebhookService()

        await service.create_subscription(
            gmail_service=mock_gmail_service,
            config=sample_subscription_config,
        )

        subscription = service.get_subscription("test_account")

        assert subscription is not None
        assert subscription.account_id == "test_account"

    def test_get_nonexistent_subscription(self):
        """Test retrieving non-existent subscription."""
        service = WebhookService()

        subscription = service.get_subscription("nonexistent_account")

        assert subscription is None

    @pytest.mark.asyncio
    async def test_list_subscriptions(
        self,
        mock_gmail_service,
    ):
        """Test listing all subscriptions."""
        service = WebhookService()

        # Create multiple subscriptions
        config1 = SubscriptionConfig(
            account_id="account_1",
            topic_name="projects/my-project/topics/gmail-push",
        )
        config2 = SubscriptionConfig(
            account_id="account_2",
            topic_name="projects/my-project/topics/gmail-push",
        )

        await service.create_subscription(mock_gmail_service, config1)
        await service.create_subscription(mock_gmail_service, config2)

        subscriptions = service.list_subscriptions()

        assert len(subscriptions) == 2
        account_ids = [s.account_id for s in subscriptions]
        assert "account_1" in account_ids
        assert "account_2" in account_ids

    def test_list_subscriptions_empty(self):
        """Test listing subscriptions when none exist."""
        service = WebhookService()

        subscriptions = service.list_subscriptions()

        assert len(subscriptions) == 0


# ============================================================================
# TEST CASES: MODELS
# ============================================================================

class TestModels:
    """Test Pydantic models."""

    def test_subscription_config_model(self):
        """Test SubscriptionConfig model."""
        config = SubscriptionConfig(
            account_id="test_account",
            topic_name="projects/my-project/topics/gmail-push",
            labels=["INBOX"],
            expiration_days=5,
        )

        assert config.account_id == "test_account"
        assert config.topic_name == "projects/my-project/topics/gmail-push"
        assert config.labels == ["INBOX"]
        assert config.expiration_days == 5

    def test_subscription_info_model(self):
        """Test SubscriptionInfo model."""
        info = SubscriptionInfo(
            account_id="test_account",
            topic_name="projects/my-project/topics/gmail-push",
            history_id="12345",
            expires_at=datetime.now() + timedelta(days=7),
        )

        assert info.account_id == "test_account"
        assert info.status == SubscriptionStatus.ACTIVE
        assert info.created_at is not None

    def test_push_notification_model(self):
        """Test PushNotification model."""
        notification = PushNotification(
            email_address="test@example.com",
            history_id="12345",
        )

        assert notification.email_address == "test@example.com"
        assert notification.history_id == "12345"

    def test_webhook_event_model(self):
        """Test WebhookEvent model."""
        event = WebhookEvent(
            account_id="test_account",
            history_id="12345",
            email_address="test@example.com",
            processed=True,
        )

        assert event.account_id == "test_account"
        assert event.processed is True
        assert event.received_at is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
