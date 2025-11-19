"""
Integration Test: Event Logging in Classification System

Tests that EMAIL_CLASSIFIED events are properly logged when emails are classified.
"""

import asyncio
from agent_platform.classification.models import EmailToClassify
from agent_platform.classification.unified_classifier import UnifiedClassifier
from agent_platform.events import get_events, EventType


async def test_classification_event_logging():
    """Test that classification logs events correctly."""
    print("=" * 80)
    print("EVENT INTEGRATION TEST: Classification Event Logging")
    print("=" * 80)
    print()

    # Create test email
    email = EmailToClassify(
        email_id='test_event_integration_001',
        subject='URGENT: Invoice #12345 - Payment Required',
        sender='billing@company.com',
        body='Please pay invoice #12345 within 7 days.',
        account_id='gmail_test_account'
    )

    print(f"📧 Test Email:")
    print(f"   Email ID: {email.email_id}")
    print(f"   Account ID: {email.account_id}")
    print(f"   Subject: {email.subject}")
    print(f"   Sender: {email.sender}")
    print()

    # Classify email
    print("🔄 Classifying email...")
    classifier = UnifiedClassifier()
    result = await classifier.classify(email)

    print(f"✅ Classification complete:")
    print(f"   Category: {result.category}")
    print(f"   Importance: {result.importance:.2f}")
    print(f"   Confidence: {result.confidence:.2f}")
    print(f"   Layer Used: {result.layer_used}")
    print(f"   Processing Time: {result.processing_time_ms:.0f}ms")
    print()

    # Check if event was logged
    print("🔍 Checking Event-Log system...")
    events = get_events(
        event_type=EventType.EMAIL_CLASSIFIED,
        email_id='test_event_integration_001',
        limit=10
    )

    print(f"✅ Found {len(events)} EMAIL_CLASSIFIED event(s)")
    print()

    if not events:
        print("❌ FAIL: No events found!")
        return False

    # Verify event details
    event = events[0]
    print("📝 Event Details:")
    print(f"   Event ID: {event.event_id}")
    print(f"   Event Type: {event.event_type}")
    print(f"   Account ID: {event.account_id}")
    print(f"   Email ID: {event.email_id}")
    print(f"   Timestamp: {event.timestamp}")
    print(f"   Processing Time: {event.processing_time_ms:.0f}ms")
    print()
    print(f"   Payload:")
    print(f"      - category: {event.payload.get('category')}")
    print(f"      - confidence: {event.payload.get('confidence'):.2f}")
    print(f"      - importance: {event.payload.get('importance'):.2f}")
    print(f"      - layer_used: {event.payload.get('layer_used')}")
    print()
    print(f"   Extra Metadata:")
    print(f"      - llm_provider: {event.extra_metadata.get('llm_provider')}")
    print()

    # Verify correctness
    assert event.account_id == 'gmail_test_account', "Account ID mismatch"
    assert event.email_id == 'test_event_integration_001', "Email ID mismatch"
    assert event.payload['category'] == result.category, "Category mismatch"
    assert event.payload['confidence'] == result.confidence, "Confidence mismatch"
    assert event.payload['importance'] == result.importance, "Importance mismatch"
    assert event.payload['layer_used'] == result.layer_used, "Layer mismatch"
    assert event.processing_time_ms == result.processing_time_ms, "Processing time mismatch"

    print("✅ All assertions passed!")
    print()
    print("=" * 80)
    print("✅ EVENT INTEGRATION TEST PASSED!")
    print("=" * 80)

    return True


if __name__ == "__main__":
    success = asyncio.run(test_classification_event_logging())
    if not success:
        exit(1)
