"""
API Routes for Gmail Webhook operations
"""

from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from typing import List, Optional
import base64
import json

from agent_platform.webhooks import (
    WebhookService,
    SubscriptionConfig,
    SubscriptionInfo,
    PushNotification,
)
from agent_platform.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

# Singleton service instance
_webhook_service: Optional[WebhookService] = None


def get_webhook_service() -> WebhookService:
    """Get or create webhook service instance"""
    global _webhook_service
    if _webhook_service is None:
        _webhook_service = WebhookService()
    return _webhook_service


@router.post("/subscriptions", response_model=SubscriptionInfo)
async def create_subscription(
    config: SubscriptionConfig,
    webhook_service: WebhookService = Depends(get_webhook_service),
):
    """
    Create a new Gmail push notification subscription

    **Parameters:**
    - account_id: Gmail account to monitor
    - topic_name: Google Cloud Pub/Sub topic (format: projects/{project}/topics/{topic})
    - labels: Optional list of Gmail label IDs to watch (default: INBOX)
    - expiration_days: Days until expiration (max 7)

    **Returns:**
    - SubscriptionInfo with subscription details

    **Note:** Requires Gmail API credentials with push notification access
    """
    try:
        # In production, get gmail_service from auth system
        # gmail_service = get_gmail_service(config.account_id)
        # subscription = await webhook_service.create_subscription(gmail_service, config)

        # For now, return mock subscription
        from datetime import datetime, timedelta
        from agent_platform.webhooks.models import SubscriptionStatus

        subscription = SubscriptionInfo(
            account_id=config.account_id,
            topic_name=config.topic_name,
            history_id="12345",
            expires_at=datetime.now() + timedelta(days=config.expiration_days),
            status=SubscriptionStatus.ACTIVE,
        )

        # Store in service
        webhook_service._active_subscriptions[config.account_id] = subscription

        logger.info(f"Created webhook subscription for {config.account_id}")

        return subscription

    except Exception as e:
        logger.error(f"Failed to create subscription: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create subscription: {str(e)}")


@router.get("/subscriptions/{account_id}", response_model=SubscriptionInfo)
async def get_subscription(
    account_id: str,
    webhook_service: WebhookService = Depends(get_webhook_service),
):
    """
    Get subscription info for an account

    **Parameters:**
    - account_id: Account to get subscription for

    **Returns:**
    - SubscriptionInfo
    """
    subscription = webhook_service.get_subscription(account_id)
    if not subscription:
        raise HTTPException(status_code=404, detail=f"No subscription found for {account_id}")

    return subscription


@router.get("/subscriptions", response_model=List[SubscriptionInfo])
async def list_subscriptions(
    webhook_service: WebhookService = Depends(get_webhook_service),
):
    """
    List all active subscriptions

    **Returns:**
    - List of SubscriptionInfo objects
    """
    return webhook_service.list_subscriptions()


@router.post("/subscriptions/{account_id}/renew", response_model=SubscriptionInfo)
async def renew_subscription(
    account_id: str,
    webhook_service: WebhookService = Depends(get_webhook_service),
):
    """
    Renew an existing subscription

    **Parameters:**
    - account_id: Account to renew subscription for

    **Returns:**
    - Updated SubscriptionInfo

    **Note:** Requires gmail_service (not implemented in mock)
    """
    subscription = webhook_service.get_subscription(account_id)
    if not subscription:
        raise HTTPException(status_code=404, detail=f"No subscription found for {account_id}")

    # In production: gmail_service = get_gmail_service(account_id)
    # renewed = await webhook_service.renew_subscription(gmail_service, account_id)

    # Mock implementation
    from datetime import datetime, timedelta
    subscription.expires_at = datetime.now() + timedelta(days=7)
    subscription.created_at = datetime.now()

    logger.info(f"Renewed subscription for {account_id}")

    return subscription


@router.delete("/subscriptions/{account_id}")
async def stop_subscription(
    account_id: str,
    webhook_service: WebhookService = Depends(get_webhook_service),
):
    """
    Stop an active subscription

    **Parameters:**
    - account_id: Account to stop subscription for

    **Returns:**
    - Success message
    """
    subscription = webhook_service.get_subscription(account_id)
    if not subscription:
        raise HTTPException(status_code=404, detail=f"No subscription found for {account_id}")

    # In production: gmail_service = get_gmail_service(account_id)
    # success = await webhook_service.stop_subscription(gmail_service, account_id)

    # Mock implementation
    from agent_platform.webhooks.models import SubscriptionStatus
    subscription.status = SubscriptionStatus.EXPIRED
    del webhook_service._active_subscriptions[account_id]

    logger.info(f"Stopped subscription for {account_id}")

    return {"status": "stopped", "account_id": account_id}


@router.post("/notifications")
async def receive_notification(
    request: Request,
    background_tasks: BackgroundTasks,
    webhook_service: WebhookService = Depends(get_webhook_service),
):
    """
    Receive Gmail push notification from Google Cloud Pub/Sub

    This endpoint is called by Google Cloud Pub/Sub when new emails arrive.

    **Request Body (from Pub/Sub):**
    ```json
    {
      "message": {
        "data": "<base64-encoded-json>",
        "messageId": "...",
        "publishTime": "..."
      },
      "subscription": "..."
    }
    ```

    **Returns:**
    - 200 OK (to acknowledge receipt)

    **Note:** Processing happens in background to avoid timeout
    """
    try:
        # Parse Pub/Sub message
        body = await request.json()
        message = body.get('message', {})

        # Decode data
        data_b64 = message.get('data', '')
        if not data_b64:
            raise HTTPException(status_code=400, detail="Missing message data")

        data_json = base64.b64decode(data_b64).decode('utf-8')
        notification_data = json.loads(data_json)

        # Create notification object
        notification = PushNotification(
            email_address=notification_data.get('emailAddress', ''),
            history_id=notification_data.get('historyId', ''),
        )

        logger.info(
            f"Received notification: email={notification.email_address}, "
            f"history_id={notification.history_id}"
        )

        # Process in background
        # In production: gmail_service = get_gmail_service(account_id)
        # background_tasks.add_task(
        #     webhook_service.handle_notification,
        #     gmail_service,
        #     notification,
        # )

        # For now, just log
        logger.info("Notification queued for processing (mock)")

        # Return 200 to acknowledge
        return {"status": "received", "message_id": message.get('messageId')}

    except Exception as e:
        logger.error(f"Failed to process notification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process notification: {str(e)}")


@router.get("/subscriptions/check-expirations")
async def check_expirations(
    webhook_service: WebhookService = Depends(get_webhook_service),
):
    """
    Check for expired subscriptions

    **Returns:**
    - List of expired account IDs
    """
    expired = webhook_service.check_expirations()
    return {"expired_accounts": expired, "count": len(expired)}
