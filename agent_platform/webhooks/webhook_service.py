"""
Gmail Webhook Service - Real-time email processing via Gmail Push Notifications

This service handles:
1. Setting up Gmail push notifications via Google Cloud Pub/Sub
2. Processing incoming webhook notifications
3. Fetching and processing new emails based on history ID
4. Managing subscription lifecycle (creation, renewal, expiration)

Gmail Push Notifications: https://developers.google.com/gmail/api/guides/push
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from googleapiclient.discovery import Resource

from agent_platform.webhooks.models import (
    SubscriptionConfig,
    SubscriptionInfo,
    SubscriptionStatus,
    PushNotification,
    WebhookEvent,
)
from agent_platform.orchestration import ClassificationOrchestrator
from agent_platform.events import log_event, EventType
from agent_platform.core.logger import get_logger

logger = get_logger(__name__)


class WebhookService:
    """Service for managing Gmail push notifications and real-time processing"""

    def __init__(self, orchestrator: Optional[ClassificationOrchestrator] = None):
        """
        Initialize webhook service

        Args:
            orchestrator: Classification orchestrator (creates new if None)
        """
        self.orchestrator = orchestrator or ClassificationOrchestrator()
        self._active_subscriptions: Dict[str, SubscriptionInfo] = {}
        self._pending_events: List[WebhookEvent] = []

    async def create_subscription(
        self,
        gmail_service: Resource,
        config: SubscriptionConfig,
    ) -> SubscriptionInfo:
        """
        Create a new Gmail push notification subscription

        Args:
            gmail_service: Gmail API service object
            config: Subscription configuration

        Returns:
            SubscriptionInfo with subscription details

        Raises:
            Exception if subscription fails
        """
        try:
            # Get current history ID
            profile = gmail_service.users().getProfile(userId='me').execute()
            history_id = profile['historyId']

            # Set up watch request
            watch_request = {
                'topicName': config.topic_name,
                'labelIds': config.labels or ['INBOX'],
            }

            # Call Gmail API to start watching
            watch_response = gmail_service.users().watch(
                userId='me',
                body=watch_request,
            ).execute()

            # Calculate expiration (Gmail max: 7 days)
            expires_at = datetime.now() + timedelta(days=min(config.expiration_days, 7))

            # Create subscription info
            subscription = SubscriptionInfo(
                account_id=config.account_id,
                topic_name=config.topic_name,
                history_id=watch_response['historyId'],
                expires_at=expires_at,
                status=SubscriptionStatus.ACTIVE,
            )

            # Store active subscription
            self._active_subscriptions[config.account_id] = subscription

            # Log event
            log_event(
                event_type=EventType.CUSTOM,
                account_id=config.account_id,
                payload={
                    'action': 'webhook_subscription_created',
                    'topic': config.topic_name,
                    'expires_at': expires_at.isoformat(),
                    'history_id': history_id,
                },
            )

            logger.info(
                f"Created webhook subscription for {config.account_id}, expires at {expires_at}"
            )

            return subscription

        except Exception as e:
            logger.error(f"Failed to create webhook subscription: {e}", exc_info=True)

            log_event(
                event_type=EventType.CUSTOM,
                account_id=config.account_id,
                payload={
                    'action': 'webhook_subscription_failed',
                    'error': str(e),
                },
            )

            raise

    async def renew_subscription(
        self,
        gmail_service: Resource,
        account_id: str,
    ) -> SubscriptionInfo:
        """
        Renew an existing subscription

        Args:
            gmail_service: Gmail API service object
            account_id: Account to renew subscription for

        Returns:
            Updated SubscriptionInfo
        """
        subscription = self._active_subscriptions.get(account_id)
        if not subscription:
            raise ValueError(f"No active subscription for {account_id}")

        # Create new subscription with same config
        config = SubscriptionConfig(
            account_id=account_id,
            topic_name=subscription.topic_name,
        )

        return await self.create_subscription(gmail_service, config)

    async def stop_subscription(
        self,
        gmail_service: Resource,
        account_id: str,
    ) -> bool:
        """
        Stop an active subscription

        Args:
            gmail_service: Gmail API service object
            account_id: Account to stop subscription for

        Returns:
            True if stopped successfully
        """
        subscription = self._active_subscriptions.get(account_id)
        if not subscription:
            return False

        try:
            # Call Gmail API to stop watching
            gmail_service.users().stop(userId='me').execute()

            # Update status
            subscription.status = SubscriptionStatus.EXPIRED

            # Remove from active subscriptions
            del self._active_subscriptions[account_id]

            log_event(
                event_type=EventType.CUSTOM,
                account_id=account_id,
                payload={'action': 'webhook_subscription_stopped'},
            )

            logger.info(f"Stopped webhook subscription for {account_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to stop webhook subscription: {e}", exc_info=True)
            return False

    async def handle_notification(
        self,
        gmail_service: Resource,
        notification: PushNotification,
    ) -> WebhookEvent:
        """
        Handle incoming Gmail push notification

        This processes the notification by:
        1. Validating the subscription
        2. Fetching new emails since last history ID
        3. Processing them through the orchestrator
        4. Updating subscription state

        Args:
            gmail_service: Gmail API service object
            notification: Push notification from Gmail

        Returns:
            WebhookEvent with processing status
        """
        # Find matching subscription
        account_id = None
        for acc_id, sub in self._active_subscriptions.items():
            if sub.history_id == notification.history_id or acc_id in notification.email_address:
                account_id = acc_id
                break

        if not account_id:
            logger.warning(f"Received notification for unknown account: {notification.email_address}")
            return WebhookEvent(
                account_id="unknown",
                history_id=notification.history_id,
                email_address=notification.email_address,
                processed=False,
                error_message="No matching subscription found",
            )

        subscription = self._active_subscriptions[account_id]

        # Create webhook event
        event = WebhookEvent(
            account_id=account_id,
            history_id=notification.history_id,
            email_address=notification.email_address,
        )

        try:
            # Fetch history changes since last notification
            new_emails = await self._fetch_history_changes(
                gmail_service,
                subscription.history_id,
                notification.history_id,
            )

            if new_emails:
                # Process new emails through orchestrator
                stats = await self.orchestrator.process_emails(new_emails, account_id)

                logger.info(
                    f"Processed {len(new_emails)} new emails for {account_id}: {stats}"
                )

                log_event(
                    event_type=EventType.CUSTOM,
                    account_id=account_id,
                    payload={
                        'action': 'webhook_emails_processed',
                        'count': len(new_emails),
                        'stats': stats,
                    },
                )

            # Update subscription state
            subscription.history_id = notification.history_id
            subscription.last_notification_at = datetime.now()

            # Mark event as processed
            event.processed = True
            event.processed_at = datetime.now()

        except Exception as e:
            logger.error(f"Failed to process webhook notification: {e}", exc_info=True)
            event.processed = False
            event.error_message = str(e)

            log_event(
                event_type=EventType.CUSTOM,
                account_id=account_id,
                payload={
                    'action': 'webhook_processing_failed',
                    'error': str(e),
                },
            )

        return event

    async def _fetch_history_changes(
        self,
        gmail_service: Resource,
        start_history_id: str,
        end_history_id: str,
    ) -> List[Dict]:
        """
        Fetch emails from Gmail history API

        Args:
            gmail_service: Gmail API service object
            start_history_id: Starting history ID
            end_history_id: Ending history ID

        Returns:
            List of new email dictionaries
        """
        new_emails = []

        try:
            # Fetch history
            history = gmail_service.users().history().list(
                userId='me',
                startHistoryId=start_history_id,
                historyTypes=['messageAdded'],
            ).execute()

            if 'history' not in history:
                return []

            # Extract message IDs
            message_ids = []
            for record in history['history']:
                if 'messagesAdded' in record:
                    for msg_added in record['messagesAdded']:
                        message_ids.append(msg_added['message']['id'])

            # Fetch full messages
            for msg_id in message_ids:
                email_data = gmail_service.users().messages().get(
                    userId='me',
                    id=msg_id,
                    format='full',
                ).execute()

                # Convert to orchestrator format
                email_dict = self._convert_gmail_to_dict(email_data)
                new_emails.append(email_dict)

        except Exception as e:
            logger.error(f"Failed to fetch history changes: {e}")

        return new_emails

    def _convert_gmail_to_dict(self, gmail_message: Dict) -> Dict:
        """Convert Gmail API message format to orchestrator format"""
        headers = {h['name']: h['value'] for h in gmail_message['payload']['headers']}

        return {
            'id': gmail_message['id'],
            'subject': headers.get('Subject', ''),
            'sender': headers.get('From', ''),
            'body': self._extract_body(gmail_message['payload']),
            'received_at': headers.get('Date', ''),
            'thread_id': gmail_message.get('threadId'),
        }

    def _extract_body(self, payload: Dict) -> str:
        """Extract body text from Gmail message payload"""
        if 'body' in payload and payload['body'].get('data'):
            import base64
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')

        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    import base64
                    return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')

        return ""

    def get_subscription(self, account_id: str) -> Optional[SubscriptionInfo]:
        """Get subscription info for an account"""
        return self._active_subscriptions.get(account_id)

    def list_subscriptions(self) -> List[SubscriptionInfo]:
        """List all active subscriptions"""
        return list(self._active_subscriptions.values())

    def check_expirations(self) -> List[str]:
        """
        Check for expired subscriptions

        Returns:
            List of expired account IDs
        """
        expired = []
        now = datetime.now()

        for account_id, subscription in list(self._active_subscriptions.items()):
            if subscription.expires_at <= now:
                subscription.status = SubscriptionStatus.EXPIRED
                expired.append(account_id)
                logger.warning(f"Subscription expired for {account_id}")

        return expired
