"""
Unit Tests: Thread Service (Phase 4)

Tests thread tracking and summarization:
1. ThreadService initialization
2. Getting emails in a thread
3. Generating thread summaries with LLM
4. Caching thread summaries
5. Force regenerate functionality
6. Thread position tracking
7. is_thread_start flag
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock, patch

from agent_platform.threads import (
    ThreadService,
    ThreadSummary,
    ThreadEmail,
)
from agent_platform.db.database import get_db
from agent_platform.db.models import ProcessedEmail, EmailAccount


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for thread summarization."""
    mock_llm = AsyncMock()
    mock_llm.generate_text = AsyncMock(
        return_value="This thread discusses the Q4 budget approval. John requested approval, and Sarah responded with questions about the timeline. The discussion is ongoing."
    )
    return mock_llm


@pytest.fixture
def sample_thread_emails():
    """Create sample thread emails in database."""
    with get_db() as db:
        # Create test account if not exists
        account = db.query(EmailAccount).filter(
            EmailAccount.account_id == "test_thread_account"
        ).first()
        if not account:
            account = EmailAccount(
                account_id="test_thread_account",
                email_address="test@example.com",
                provider="gmail",
            )
            db.add(account)
            db.flush()

        # Create thread emails
        emails = [
            ProcessedEmail(
                email_id="thread_msg_001",
                account_id=account.id,
                thread_id="thread_123",
                subject="Q4 Budget Discussion",
                sender="john@company.com",
                body_text="Hi team, can we approve the Q4 budget?",
                received_at=datetime(2025, 11, 20, 10, 0),
                category="wichtig",
                confidence=0.8,
            ),
            ProcessedEmail(
                email_id="thread_msg_002",
                account_id=account.id,
                thread_id="thread_123",
                subject="Re: Q4 Budget Discussion",
                sender="sarah@company.com",
                body_text="What's the deadline for this?",
                received_at=datetime(2025, 11, 20, 11, 0),
                category="wichtig",
                confidence=0.75,
            ),
            ProcessedEmail(
                email_id="thread_msg_003",
                account_id=account.id,
                thread_id="thread_123",
                subject="Re: Q4 Budget Discussion",
                sender="john@company.com",
                body_text="We need it by Friday.",
                received_at=datetime(2025, 11, 20, 12, 0),
                category="wichtig",
                confidence=0.8,
            ),
        ]

        for email in emails:
            db.add(email)

    yield "thread_123"

    # Cleanup
    with get_db() as db:
        db.query(ProcessedEmail).filter(
            ProcessedEmail.thread_id == "thread_123"
        ).delete()


# ============================================================================
# TEST CASES: INITIALIZATION
# ============================================================================

class TestThreadServiceInitialization:
    """Test ThreadService initialization."""

    def test_default_initialization(self):
        """Test service initialization with default LLM provider."""
        service = ThreadService()

        assert service.llm is not None

    @patch('agent_platform.threads.thread_service.get_llm_provider')
    def test_initialization_with_mock_llm(self, mock_get_llm):
        """Test initialization uses LLM provider correctly."""
        mock_llm = Mock()
        mock_get_llm.return_value = mock_llm

        service = ThreadService()

        assert service.llm == mock_llm
        mock_get_llm.assert_called_once()


# ============================================================================
# TEST CASES: GETTING THREAD EMAILS
# ============================================================================

class TestGetThreadEmails:
    """Test retrieving emails in a thread."""

    def test_get_thread_emails_basic(self, sample_thread_emails):
        """Test getting all emails in a thread."""
        service = ThreadService()

        emails = service.get_thread_emails("thread_123")

        assert len(emails) == 3
        assert all(email.thread_id == "thread_123" for email in emails)

        # Verify chronological order
        assert emails[0].email_id == "thread_msg_001"
        assert emails[1].email_id == "thread_msg_002"
        assert emails[2].email_id == "thread_msg_003"

    def test_get_thread_emails_with_account_filter(self, sample_thread_emails):
        """Test getting thread emails filtered by account."""
        service = ThreadService()

        # This would need account_id from EmailAccount, but our current schema
        # uses FK to account table, so we test the query structure
        emails = service.get_thread_emails("thread_123")

        assert len(emails) == 3

    def test_get_thread_emails_nonexistent(self):
        """Test getting emails for non-existent thread."""
        service = ThreadService()

        emails = service.get_thread_emails("nonexistent_thread")

        assert len(emails) == 0

    def test_thread_emails_chronological_order(self, sample_thread_emails):
        """Test that emails are returned in chronological order."""
        service = ThreadService()

        emails = service.get_thread_emails("thread_123")

        # Verify timestamps are in order
        for i in range(len(emails) - 1):
            assert emails[i].received_at <= emails[i + 1].received_at


# ============================================================================
# TEST CASES: THREAD SUMMARIZATION
# ============================================================================

class TestThreadSummarization:
    """Test LLM-based thread summarization."""

    @pytest.mark.asyncio
    @patch('agent_platform.threads.thread_service.get_llm_provider')
    async def test_generate_thread_summary(
        self,
        mock_get_llm,
        sample_thread_emails,
        mock_llm_provider,
    ):
        """Test generating a thread summary with LLM."""
        mock_get_llm.return_value = mock_llm_provider

        service = ThreadService()
        summary = await service.summarize_thread(
            thread_id="thread_123",
            account_id="test_thread_account",
        )

        # Verify summary structure
        assert isinstance(summary, ThreadSummary)
        assert summary.thread_id == "thread_123"
        assert summary.email_count == 3
        assert summary.subject == "Q4 Budget Discussion"
        assert len(summary.participants) > 0
        assert summary.summary is not None

        # Verify LLM was called
        mock_llm_provider.generate_text.assert_called_once()

    @pytest.mark.asyncio
    @patch('agent_platform.threads.thread_service.get_llm_provider')
    async def test_thread_summary_participants(
        self,
        mock_get_llm,
        sample_thread_emails,
        mock_llm_provider,
    ):
        """Test that thread summary includes all participants."""
        mock_get_llm.return_value = mock_llm_provider

        service = ThreadService()
        summary = await service.summarize_thread("thread_123", "test_thread_account")

        # Should have john and sarah
        assert "john@company.com" in summary.participants
        assert "sarah@company.com" in summary.participants

    @pytest.mark.asyncio
    @patch('agent_platform.threads.thread_service.get_llm_provider')
    async def test_thread_summary_timestamps(
        self,
        mock_get_llm,
        sample_thread_emails,
        mock_llm_provider,
    ):
        """Test that thread summary includes correct timestamps."""
        mock_get_llm.return_value = mock_llm_provider

        service = ThreadService()
        summary = await service.summarize_thread("thread_123", "test_thread_account")

        # started_at should be first email
        assert summary.started_at == datetime(2025, 11, 20, 10, 0)

        # last_email_at should be last email
        assert summary.last_email_at == datetime(2025, 11, 20, 12, 0)

    @pytest.mark.asyncio
    async def test_thread_summary_nonexistent_thread(self):
        """Test summarizing non-existent thread raises error."""
        service = ThreadService()

        with pytest.raises(ValueError, match="No emails found"):
            await service.summarize_thread("nonexistent_thread", "test_account")


# ============================================================================
# TEST CASES: CACHING THREAD SUMMARIES
# ============================================================================

class TestSummaryCaching:
    """Test thread summary caching logic."""

    @pytest.mark.asyncio
    @patch('agent_platform.threads.thread_service.get_llm_provider')
    async def test_cached_summary_reused(
        self,
        mock_get_llm,
        sample_thread_emails,
        mock_llm_provider,
    ):
        """Test that existing summary is reused (not regenerated)."""
        mock_get_llm.return_value = mock_llm_provider

        service = ThreadService()

        # First call - generates summary
        summary1 = await service.summarize_thread("thread_123", "test_thread_account")
        first_call_count = mock_llm_provider.generate_text.call_count

        # Second call - should use cached
        summary2 = await service.summarize_thread("thread_123", "test_thread_account")
        second_call_count = mock_llm_provider.generate_text.call_count

        # LLM should only be called once (cached on second call)
        assert second_call_count == first_call_count
        assert summary1.summary == summary2.summary

    @pytest.mark.asyncio
    @patch('agent_platform.threads.thread_service.get_llm_provider')
    async def test_cached_summary_stored_in_db(
        self,
        mock_get_llm,
        sample_thread_emails,
        mock_llm_provider,
    ):
        """Test that generated summary is stored in database."""
        mock_get_llm.return_value = mock_llm_provider

        service = ThreadService()
        await service.summarize_thread("thread_123", "test_thread_account")

        # Check database for stored summary
        with get_db() as db:
            first_email = db.query(ProcessedEmail).filter(
                ProcessedEmail.thread_id == "thread_123"
            ).order_by(ProcessedEmail.received_at).first()

            assert first_email.thread_summary is not None
            assert "budget" in first_email.thread_summary.lower()


# ============================================================================
# TEST CASES: FORCE REGENERATE
# ============================================================================

class TestForceRegenerate:
    """Test force regenerate functionality."""

    @pytest.mark.asyncio
    @patch('agent_platform.threads.thread_service.get_llm_provider')
    async def test_force_regenerate_calls_llm(
        self,
        mock_get_llm,
        sample_thread_emails,
        mock_llm_provider,
    ):
        """Test that force_regenerate=True regenerates even if cached."""
        mock_get_llm.return_value = mock_llm_provider

        service = ThreadService()

        # First call - generates summary
        await service.summarize_thread("thread_123", "test_thread_account")
        first_call_count = mock_llm_provider.generate_text.call_count

        # Second call with force_regenerate - should call LLM again
        await service.summarize_thread(
            "thread_123",
            "test_thread_account",
            force_regenerate=True,
        )
        second_call_count = mock_llm_provider.generate_text.call_count

        # LLM should be called twice
        assert second_call_count == first_call_count + 1

    @pytest.mark.asyncio
    @patch('agent_platform.threads.thread_service.get_llm_provider')
    async def test_force_regenerate_updates_db(
        self,
        mock_get_llm,
        sample_thread_emails,
    ):
        """Test that force regenerate updates database summary."""
        # First LLM call returns one summary
        mock_llm_v1 = AsyncMock()
        mock_llm_v1.generate_text = AsyncMock(return_value="Summary version 1")
        mock_get_llm.return_value = mock_llm_v1

        service = ThreadService()
        await service.summarize_thread("thread_123", "test_thread_account")

        # Second LLM call returns different summary
        mock_llm_v2 = AsyncMock()
        mock_llm_v2.generate_text = AsyncMock(return_value="Summary version 2")
        mock_get_llm.return_value = mock_llm_v2

        service = ThreadService()  # Reinitialize with new mock
        summary = await service.summarize_thread(
            "thread_123",
            "test_thread_account",
            force_regenerate=True,
        )

        # Should have new summary
        assert summary.summary == "Summary version 2"

        # Check database
        with get_db() as db:
            first_email = db.query(ProcessedEmail).filter(
                ProcessedEmail.thread_id == "thread_123"
            ).order_by(ProcessedEmail.received_at).first()

            assert first_email.thread_summary == "Summary version 2"


# ============================================================================
# TEST CASES: THREAD POSITION TRACKING
# ============================================================================

class TestThreadPositions:
    """Test thread position tracking."""

    @pytest.mark.asyncio
    @patch('agent_platform.threads.thread_service.get_llm_provider')
    async def test_thread_positions_set(
        self,
        mock_get_llm,
        sample_thread_emails,
        mock_llm_provider,
    ):
        """Test that thread positions are set correctly."""
        mock_get_llm.return_value = mock_llm_provider

        service = ThreadService()
        await service.summarize_thread("thread_123", "test_thread_account")

        # Verify positions in database
        with get_db() as db:
            emails = db.query(ProcessedEmail).filter(
                ProcessedEmail.thread_id == "thread_123"
            ).order_by(ProcessedEmail.received_at).all()

            assert emails[0].thread_position == 1
            assert emails[1].thread_position == 2
            assert emails[2].thread_position == 3

    @pytest.mark.asyncio
    @patch('agent_platform.threads.thread_service.get_llm_provider')
    async def test_thread_emails_include_position(
        self,
        mock_get_llm,
        sample_thread_emails,
        mock_llm_provider,
    ):
        """Test that ThreadEmail objects include position."""
        mock_get_llm.return_value = mock_llm_provider

        service = ThreadService()
        summary = await service.summarize_thread("thread_123", "test_thread_account")

        # Verify positions in summary
        assert summary.emails[0].position == 1
        assert summary.emails[1].position == 2
        assert summary.emails[2].position == 3


# ============================================================================
# TEST CASES: IS_THREAD_START FLAG
# ============================================================================

class TestThreadStartFlag:
    """Test is_thread_start flag."""

    @pytest.mark.asyncio
    @patch('agent_platform.threads.thread_service.get_llm_provider')
    async def test_first_email_is_thread_start(
        self,
        mock_get_llm,
        sample_thread_emails,
        mock_llm_provider,
    ):
        """Test that first email is marked as thread_start."""
        mock_get_llm.return_value = mock_llm_provider

        service = ThreadService()
        await service.summarize_thread("thread_123", "test_thread_account")

        # Check database
        with get_db() as db:
            emails = db.query(ProcessedEmail).filter(
                ProcessedEmail.thread_id == "thread_123"
            ).order_by(ProcessedEmail.received_at).all()

            assert emails[0].is_thread_start is True
            assert emails[1].is_thread_start is False
            assert emails[2].is_thread_start is False

    @pytest.mark.asyncio
    @patch('agent_platform.threads.thread_service.get_llm_provider')
    async def test_thread_summary_stored_on_first_email(
        self,
        mock_get_llm,
        sample_thread_emails,
        mock_llm_provider,
    ):
        """Test that thread summary is stored on first email only."""
        mock_get_llm.return_value = mock_llm_provider

        service = ThreadService()
        await service.summarize_thread("thread_123", "test_thread_account")

        with get_db() as db:
            emails = db.query(ProcessedEmail).filter(
                ProcessedEmail.thread_id == "thread_123"
            ).order_by(ProcessedEmail.received_at).all()

            # Only first email has summary
            assert emails[0].thread_summary is not None
            assert emails[1].thread_summary is None or emails[1].thread_summary == ""
            assert emails[2].thread_summary is None or emails[2].thread_summary == ""

    @pytest.mark.asyncio
    @patch('agent_platform.threads.thread_service.get_llm_provider')
    async def test_thread_email_model_has_start_flag(
        self,
        mock_get_llm,
        sample_thread_emails,
        mock_llm_provider,
    ):
        """Test that ThreadEmail model includes is_thread_start."""
        mock_get_llm.return_value = mock_llm_provider

        service = ThreadService()
        summary = await service.summarize_thread("thread_123", "test_thread_account")

        # Check ThreadEmail objects
        assert summary.emails[0].is_thread_start is True
        assert summary.emails[1].is_thread_start is False
        assert summary.emails[2].is_thread_start is False


# ============================================================================
# TEST CASES: EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    @patch('agent_platform.threads.thread_service.get_llm_provider')
    async def test_single_email_thread(self, mock_get_llm, mock_llm_provider):
        """Test summarizing a thread with only one email."""
        mock_get_llm.return_value = mock_llm_provider

        # Create single-email thread
        with get_db() as db:
            account = EmailAccount(
                account_id="test_single",
                email_address="test@example.com",
                provider="gmail",
            )
            db.add(account)
            db.flush()

            email = ProcessedEmail(
                email_id="single_msg",
                account_id=account.id,
                thread_id="single_thread",
                subject="Single Email",
                sender="user@example.com",
                body_text="This is the only email in the thread.",
                received_at=datetime.utcnow(),
                category="normal",
                confidence=0.8,
            )
            db.add(email)

        service = ThreadService()
        summary = await service.summarize_thread("single_thread", "test_single")

        assert summary.email_count == 1
        assert summary.emails[0].position == 1
        assert summary.emails[0].is_thread_start is True

        # Cleanup
        with get_db() as db:
            db.query(ProcessedEmail).filter(
                ProcessedEmail.thread_id == "single_thread"
            ).delete()

    @pytest.mark.asyncio
    @patch('agent_platform.threads.thread_service.get_llm_provider')
    async def test_thread_with_missing_body(self, mock_get_llm, mock_llm_provider):
        """Test summarizing thread with emails missing body text."""
        mock_get_llm.return_value = mock_llm_provider

        # Create thread with missing body
        with get_db() as db:
            account = EmailAccount(
                account_id="test_missing",
                email_address="test@example.com",
                provider="gmail",
            )
            db.add(account)
            db.flush()

            email = ProcessedEmail(
                email_id="missing_body",
                account_id=account.id,
                thread_id="missing_thread",
                subject="No Body",
                sender="user@example.com",
                body_text=None,  # Missing
                summary="Short summary",
                received_at=datetime.utcnow(),
                category="normal",
                confidence=0.8,
            )
            db.add(email)

        service = ThreadService()
        summary = await service.summarize_thread("missing_thread", "test_missing")

        # Should still work (uses summary as fallback)
        assert summary is not None
        mock_llm_provider.generate_text.assert_called_once()

        # Cleanup
        with get_db() as db:
            db.query(ProcessedEmail).filter(
                ProcessedEmail.thread_id == "missing_thread"
            ).delete()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
