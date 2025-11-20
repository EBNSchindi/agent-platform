"""
Pydantic models for Gmail Webhook system
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class SubscriptionStatus(str, Enum):
    """Status of a Gmail push notification subscription"""
    ACTIVE = "active"
    EXPIRED = "expired"
    FAILED = "failed"


class SubscriptionConfig(BaseModel):
    """Configuration for Gmail push notifications"""
    account_id: str = Field(..., description="Gmail account ID")
    topic_name: str = Field(..., description="Google Cloud Pub/Sub topic name")
    labels: Optional[list[str]] = Field(default=None, description="Gmail label IDs to watch (None = all)")
    expiration_days: int = Field(default=7, ge=1, le=7, description="Subscription expiration in days (max 7)")


class SubscriptionInfo(BaseModel):
    """Information about an active subscription"""
    account_id: str
    topic_name: str
    history_id: str = Field(..., description="Gmail history ID at subscription time")
    expires_at: datetime = Field(..., description="When subscription expires")
    status: SubscriptionStatus = Field(default=SubscriptionStatus.ACTIVE)
    created_at: datetime = Field(default_factory=datetime.now)
    last_notification_at: Optional[datetime] = Field(default=None)


class PushNotification(BaseModel):
    """
    Gmail push notification payload

    See: https://developers.google.com/gmail/api/guides/push
    """
    email_address: str = Field(..., description="Email address of the account")
    history_id: str = Field(..., description="New history ID")

    class Config:
        # Allow extra fields from Pub/Sub
        extra = "allow"


class WebhookEvent(BaseModel):
    """Internal webhook event for processing"""
    account_id: str
    history_id: str
    email_address: str
    received_at: datetime = Field(default_factory=datetime.now)
    processed: bool = Field(default=False)
    processed_at: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
