"""
Event Service for Digital Twin Platform

Provides functions to log and query events in the system.
All events are APPEND-ONLY (immutable).

Usage:
    from agent_platform.events import log_event, EventType

    # Log an event
    event = log_event(
        event_type=EventType.EMAIL_CLASSIFIED,
        account_id="gmail_1",
        email_id="msg_123",
        payload={
            'category': 'wichtig',
            'confidence': 0.92,
            'layer_used': 'llm'
        }
    )

    # Query events
    events = get_events(
        event_type=EventType.EMAIL_CLASSIFIED,
        account_id="gmail_1",
        limit=10
    )
"""

import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from agent_platform.db.database import get_db
from agent_platform.db.models import Event
from agent_platform.events.event_types import EventType


class EventService:
    """
    Service for logging and querying events.

    This service provides a clean API for event management while
    handling database connections and error handling.
    """

    @staticmethod
    def log_event(
        event_type: EventType | str,
        account_id: Optional[str] = None,
        email_id: Optional[str] = None,
        user_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
        processing_time_ms: Optional[float] = None,
        db: Optional[Session] = None,
    ) -> Event:
        """
        Log an event to the database.

        Args:
            event_type: Type of event (EventType enum or string)
            account_id: Account ID (e.g., 'gmail_1')
            email_id: Email ID (if applicable)
            user_id: User ID (for multi-user support)
            payload: Event-specific data (dict)
            extra_metadata: Additional context (dict)
            processing_time_ms: Processing time in milliseconds
            db: Database session (optional, will create one if not provided)

        Returns:
            Event: The created event object

        Example:
            event = EventService.log_event(
                event_type=EventType.EMAIL_CLASSIFIED,
                account_id="gmail_1",
                email_id="msg_123",
                payload={'category': 'wichtig', 'confidence': 0.92}
            )
        """
        # Convert EventType enum to string if needed
        event_type_str = event_type.value if isinstance(event_type, EventType) else event_type

        # Create event object
        event = Event(
            event_type=event_type_str,
            timestamp=datetime.utcnow(),
            account_id=account_id,
            email_id=email_id,
            user_id=user_id,
            payload=payload or {},
            extra_metadata=extra_metadata or {},
            processing_time_ms=processing_time_ms,
        )

        # Save to database
        if db:
            # Use provided session
            db.add(event)
            db.commit()
            db.refresh(event)
            return event
        else:
            # Create new session
            with get_db() as session:
                session.add(event)
                session.commit()
                session.refresh(event)
                # Detach from session before returning
                session.expunge(event)
                return event

    @staticmethod
    def get_events(
        event_type: Optional[EventType | str] = None,
        account_id: Optional[str] = None,
        email_id: Optional[str] = None,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "desc",  # 'asc' or 'desc'
        db: Optional[Session] = None,
    ) -> List[Event]:
        """
        Query events from the database.

        Args:
            event_type: Filter by event type
            account_id: Filter by account ID
            email_id: Filter by email ID
            user_id: Filter by user ID
            start_time: Filter events after this time
            end_time: Filter events before this time
            limit: Maximum number of events to return
            offset: Number of events to skip
            order_by: Sort order ('asc' or 'desc')
            db: Database session (optional)

        Returns:
            List[Event]: List of events matching the criteria

        Example:
            # Get last 10 classified emails
            events = EventService.get_events(
                event_type=EventType.EMAIL_CLASSIFIED,
                account_id="gmail_1",
                limit=10
            )
        """
        # Convert EventType enum to string if needed
        event_type_str = None
        if event_type:
            event_type_str = event_type.value if isinstance(event_type, EventType) else event_type

        # Query function
        def _query(session: Session) -> List[Event]:
            query = session.query(Event)

            # Apply filters
            if event_type_str:
                query = query.filter(Event.event_type == event_type_str)

            if account_id:
                query = query.filter(Event.account_id == account_id)

            if email_id:
                query = query.filter(Event.email_id == email_id)

            if user_id:
                query = query.filter(Event.user_id == user_id)

            if start_time:
                query = query.filter(Event.timestamp >= start_time)

            if end_time:
                query = query.filter(Event.timestamp <= end_time)

            # Apply ordering
            if order_by == "asc":
                query = query.order_by(Event.timestamp.asc())
            else:
                query = query.order_by(Event.timestamp.desc())

            # Apply pagination
            query = query.limit(limit).offset(offset)

            return query.all()

        # Execute query
        if db:
            return _query(db)
        else:
            with get_db() as session:
                events = _query(session)
                # Detach all events from session before returning
                for event in events:
                    session.expunge(event)
                return events

    @staticmethod
    def get_events_by_type(
        event_types: List[EventType | str],
        **kwargs
    ) -> List[Event]:
        """
        Get events matching any of the given event types.

        Args:
            event_types: List of event types to match
            **kwargs: Additional filters (same as get_events)

        Returns:
            List[Event]: Events matching any of the given types

        Example:
            # Get all extraction events
            events = EventService.get_events_by_type(
                event_types=[
                    EventType.TASK_EXTRACTED,
                    EventType.DECISION_EXTRACTED,
                    EventType.QUESTION_EXTRACTED
                ],
                account_id="gmail_1"
            )
        """
        # Convert to strings
        type_strings = [
            et.value if isinstance(et, EventType) else et
            for et in event_types
        ]

        db = kwargs.pop('db', None)
        limit = kwargs.pop('limit', 100)
        offset = kwargs.pop('offset', 0)
        order_by = kwargs.pop('order_by', 'desc')

        def _query(session: Session) -> List[Event]:
            query = session.query(Event)

            # Filter by event types (IN clause)
            query = query.filter(Event.event_type.in_(type_strings))

            # Apply other filters from kwargs
            if 'account_id' in kwargs:
                query = query.filter(Event.account_id == kwargs['account_id'])
            if 'email_id' in kwargs:
                query = query.filter(Event.email_id == kwargs['email_id'])
            if 'user_id' in kwargs:
                query = query.filter(Event.user_id == kwargs['user_id'])
            if 'start_time' in kwargs:
                query = query.filter(Event.timestamp >= kwargs['start_time'])
            if 'end_time' in kwargs:
                query = query.filter(Event.timestamp <= kwargs['end_time'])

            # Apply ordering
            if order_by == "asc":
                query = query.order_by(Event.timestamp.asc())
            else:
                query = query.order_by(Event.timestamp.desc())

            # Apply pagination
            query = query.limit(limit).offset(offset)

            return query.all()

        if db:
            return _query(db)
        else:
            with get_db() as session:
                events = _query(session)
                # Detach all events from session before returning
                for event in events:
                    session.expunge(event)
                return events

    @staticmethod
    def get_events_for_email(
        email_id: str,
        account_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> List[Event]:
        """
        Get all events related to a specific email.

        Args:
            email_id: Email ID
            account_id: Account ID (optional filter)
            db: Database session (optional)

        Returns:
            List[Event]: All events for this email, ordered by timestamp

        Example:
            events = EventService.get_events_for_email(
                email_id="msg_123",
                account_id="gmail_1"
            )
        """
        return EventService.get_events(
            email_id=email_id,
            account_id=account_id,
            limit=1000,  # Get all events for this email
            order_by="asc",  # Chronological order
            db=db,
        )

    @staticmethod
    def get_events_today(
        account_id: Optional[str] = None,
        event_type: Optional[EventType | str] = None,
        db: Optional[Session] = None,
    ) -> List[Event]:
        """
        Get events from today.

        Args:
            account_id: Filter by account ID
            event_type: Filter by event type
            db: Database session (optional)

        Returns:
            List[Event]: Events from today

        Example:
            events = EventService.get_events_today(
                account_id="gmail_1",
                event_type=EventType.EMAIL_CLASSIFIED
            )
        """
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        return EventService.get_events(
            event_type=event_type,
            account_id=account_id,
            start_time=today_start,
            limit=10000,  # Get all events from today
            db=db,
        )

    @staticmethod
    def count_events(
        event_type: Optional[EventType | str] = None,
        account_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        db: Optional[Session] = None,
    ) -> int:
        """
        Count events matching the given criteria.

        Args:
            event_type: Filter by event type
            account_id: Filter by account ID
            start_time: Filter events after this time
            end_time: Filter events before this time
            db: Database session (optional)

        Returns:
            int: Number of events

        Example:
            count = EventService.count_events(
                event_type=EventType.EMAIL_CLASSIFIED,
                account_id="gmail_1"
            )
        """
        event_type_str = None
        if event_type:
            event_type_str = event_type.value if isinstance(event_type, EventType) else event_type

        def _count(session: Session) -> int:
            query = session.query(Event)

            if event_type_str:
                query = query.filter(Event.event_type == event_type_str)
            if account_id:
                query = query.filter(Event.account_id == account_id)
            if start_time:
                query = query.filter(Event.timestamp >= start_time)
            if end_time:
                query = query.filter(Event.timestamp <= end_time)

            return query.count()

        if db:
            return _count(db)
        else:
            with get_db() as session:
                return _count(session)


# Convenience functions (module-level API)

def log_event(
    event_type: EventType | str,
    **kwargs
) -> Event:
    """
    Log an event (convenience function).

    See EventService.log_event() for full documentation.
    """
    return EventService.log_event(event_type=event_type, **kwargs)


def get_events(**kwargs) -> List[Event]:
    """
    Query events (convenience function).

    See EventService.get_events() for full documentation.
    """
    return EventService.get_events(**kwargs)


def get_events_for_email(email_id: str, **kwargs) -> List[Event]:
    """
    Get all events for an email (convenience function).

    See EventService.get_events_for_email() for full documentation.
    """
    return EventService.get_events_for_email(email_id=email_id, **kwargs)


def count_events(**kwargs) -> int:
    """
    Count events (convenience function).

    See EventService.count_events() for full documentation.
    """
    return EventService.count_events(**kwargs)
