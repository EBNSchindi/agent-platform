"""
Tests for Event Service

Tests the event logging and querying functionality.
"""

from datetime import datetime, timedelta

from agent_platform.events import EventService, EventType, log_event, get_events
from agent_platform.db.database import get_db
from agent_platform.db.models import Event


class TestEventService:
    """Test Event Service functionality"""

    def test_log_event_basic(self):
        """Test basic event logging"""
        event = log_event(
            event_type=EventType.EMAIL_RECEIVED,
            account_id="gmail_1",
            email_id="msg_123",
            payload={
                'sender': 'test@example.com',
                'subject': 'Test Email'
            }
        )

        assert event is not None
        assert event.event_id is not None
        assert event.event_type == EventType.EMAIL_RECEIVED.value
        assert event.account_id == "gmail_1"
        assert event.email_id == "msg_123"
        assert event.payload['sender'] == 'test@example.com'
        print(f"✅ Event logged: {event.event_id}")

    def test_log_event_with_metadata(self):
        """Test logging event with extra_metadata"""
        event = log_event(
            event_type=EventType.EMAIL_CLASSIFIED,
            account_id="gmail_1",
            email_id="msg_456",
            payload={
                'category': 'wichtig',
                'confidence': 0.92,
                'layer_used': 'llm'
            },
            extra_metadata={
                'llm_model': 'gpt-4o',
                'processing_time_ms': 1234.5
            },
            processing_time_ms=1234.5
        )

        assert event.payload['category'] == 'wichtig'
        assert event.payload['confidence'] == 0.92
        assert event.extra_metadata['llm_model'] == 'gpt-4o'
        assert event.processing_time_ms == 1234.5
        print(f"✅ Event with extra_metadata logged: {event.event_id}")

    def test_get_events_by_type(self):
        """Test querying events by type"""
        # Log some events
        log_event(
            event_type=EventType.EMAIL_RECEIVED,
            account_id="gmail_1",
            email_id="msg_001"
        )
        log_event(
            event_type=EventType.EMAIL_CLASSIFIED,
            account_id="gmail_1",
            email_id="msg_001"
        )
        log_event(
            event_type=EventType.EMAIL_RECEIVED,
            account_id="gmail_1",
            email_id="msg_002"
        )

        # Query EMAIL_RECEIVED events
        events = get_events(
            event_type=EventType.EMAIL_RECEIVED,
            account_id="gmail_1",
            limit=10
        )

        assert len(events) >= 2  # At least the 2 we just created
        for event in events:
            assert event.event_type == EventType.EMAIL_RECEIVED.value
            assert event.account_id == "gmail_1"
        print(f"✅ Found {len(events)} EMAIL_RECEIVED events")

    def test_get_events_for_email(self):
        """Test getting all events for a specific email"""
        email_id = "msg_test_email"

        # Log multiple events for same email
        log_event(
            event_type=EventType.EMAIL_RECEIVED,
            email_id=email_id,
            account_id="gmail_1"
        )
        log_event(
            event_type=EventType.EMAIL_CLASSIFIED,
            email_id=email_id,
            account_id="gmail_1"
        )
        log_event(
            event_type=EventType.TASK_EXTRACTED,
            email_id=email_id,
            account_id="gmail_1"
        )

        # Get all events for this email
        events = EventService.get_events_for_email(
            email_id=email_id,
            account_id="gmail_1"
        )

        assert len(events) >= 3
        for event in events:
            assert event.email_id == email_id
        print(f"✅ Found {len(events)} events for email {email_id}")

    def test_get_events_today(self):
        """Test getting events from today"""
        # Log an event today
        log_event(
            event_type=EventType.EMAIL_CLASSIFIED,
            account_id="gmail_1",
            payload={'test': 'today'}
        )

        # Get today's events
        events = EventService.get_events_today(
            account_id="gmail_1",
            event_type=EventType.EMAIL_CLASSIFIED
        )

        assert len(events) >= 1
        # Check that all events are from today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        for event in events:
            assert event.timestamp >= today_start
        print(f"✅ Found {len(events)} events from today")

    def test_count_events(self):
        """Test counting events"""
        # Log some events
        for i in range(5):
            log_event(
                event_type=EventType.TASK_EXTRACTED,
                account_id="gmail_2",
                email_id=f"msg_{i}"
            )

        # Count events
        count = EventService.count_events(
            event_type=EventType.TASK_EXTRACTED,
            account_id="gmail_2"
        )

        assert count >= 5
        print(f"✅ Found {count} TASK_EXTRACTED events for gmail_2")

    def test_get_events_by_multiple_types(self):
        """Test querying events by multiple types"""
        # Log different types of events
        log_event(
            event_type=EventType.TASK_EXTRACTED,
            account_id="gmail_3",
            email_id="msg_multi"
        )
        log_event(
            event_type=EventType.DECISION_EXTRACTED,
            account_id="gmail_3",
            email_id="msg_multi"
        )
        log_event(
            event_type=EventType.QUESTION_EXTRACTED,
            account_id="gmail_3",
            email_id="msg_multi"
        )

        # Get all extraction events
        events = EventService.get_events_by_type(
            event_types=[
                EventType.TASK_EXTRACTED,
                EventType.DECISION_EXTRACTED,
                EventType.QUESTION_EXTRACTED
            ],
            account_id="gmail_3"
        )

        assert len(events) >= 3
        event_types = {event.event_type for event in events}
        assert EventType.TASK_EXTRACTED.value in event_types
        assert EventType.DECISION_EXTRACTED.value in event_types
        assert EventType.QUESTION_EXTRACTED.value in event_types
        print(f"✅ Found {len(events)} extraction events")

    def test_event_ordering(self):
        """Test event ordering (asc vs desc)"""
        # Log events with slight delay
        import time
        email_id = "msg_order_test_unique"

        log_event(event_type=EventType.EMAIL_RECEIVED, email_id=email_id)
        time.sleep(0.01)
        log_event(event_type=EventType.EMAIL_CLASSIFIED, email_id=email_id)
        time.sleep(0.01)
        log_event(event_type=EventType.TASK_EXTRACTED, email_id=email_id)

        # Get events in ascending order (oldest first) - default for get_events_for_email
        events_asc = EventService.get_events_for_email(email_id=email_id)
        assert len(events_asc) == 3, f"Expected 3 events, got {len(events_asc)}"
        assert events_asc[0].event_type == EventType.EMAIL_RECEIVED.value
        assert events_asc[-1].event_type == EventType.TASK_EXTRACTED.value

        # Get events in descending order (newest first)
        events_desc = get_events(
            email_id=email_id,
            order_by="desc",
            limit=100
        )
        assert len(events_desc) == 3, f"Expected 3 events, got {len(events_desc)}"
        assert events_desc[0].event_type == EventType.TASK_EXTRACTED.value
        assert events_desc[-1].event_type == EventType.EMAIL_RECEIVED.value
        print("✅ Event ordering works correctly")

    def test_event_to_dict(self):
        """Test converting event to dictionary"""
        event = log_event(
            event_type=EventType.USER_FEEDBACK,
            account_id="gmail_1",
            email_id="msg_feedback",
            payload={
                'action': 'reply',
                'sentiment': 'positive'
            },
            extra_metadata={
                'source': 'gmail_ui'
            }
        )

        event_dict = event.to_dict()

        assert event_dict['event_id'] == event.event_id
        assert event_dict['event_type'] == EventType.USER_FEEDBACK.value
        assert event_dict['account_id'] == "gmail_1"
        assert event_dict['email_id'] == "msg_feedback"
        assert event_dict['payload']['action'] == 'reply'
        assert event_dict['extra_metadata']['source'] == 'gmail_ui'
        print("✅ Event to_dict() works correctly")


if __name__ == "__main__":
    print("=" * 80)
    print("EVENT SERVICE TESTS")
    print("=" * 80)
    print()

    test = TestEventService()

    tests = [
        ("Log Event Basic", test.test_log_event_basic),
        ("Log Event with Metadata", test.test_log_event_with_metadata),
        ("Get Events by Type", test.test_get_events_by_type),
        ("Get Events for Email", test.test_get_events_for_email),
        ("Get Events Today", test.test_get_events_today),
        ("Count Events", test.test_count_events),
        ("Get Events by Multiple Types", test.test_get_events_by_multiple_types),
        ("Event Ordering", test.test_event_ordering),
        ("Event to Dict", test.test_event_to_dict),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            print(f"Running: {name}...")
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ FAILED: {name}")
            print(f"   Error: {e}")
            failed += 1

    print()
    print("=" * 80)
    print(f"Results: {passed}/{len(tests)} tests passed")
    if failed == 0:
        print("✅ ALL TESTS PASSED!")
    else:
        print(f"❌ {failed} tests failed")
    print("=" * 80)
