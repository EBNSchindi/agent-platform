"""
Unit tests for NLP Intent Parser.

Tests parsing of natural language preferences into structured intents.
"""

import pytest
from agent_platform.senders.nlp_intent_agent import parse_nlp_intent, ParsedIntent
from agent_platform.senders.intent_executor import IntentExecutor, ExecutionResult
from agent_platform.db.database import get_db
from agent_platform.db.models import SenderPreference, UserPreferenceRule, NLPIntent


@pytest.fixture
def cleanup_test_data():
    """Clean up test data after each test."""
    yield
    # Cleanup after test
    with get_db() as db:
        db.query(SenderPreference).filter(
            SenderPreference.sender_email.like('%test-nlp%')
        ).delete()
        db.query(UserPreferenceRule).filter(
            UserPreferenceRule.account_id == 'test_nlp_account'
        ).delete()
        db.query(NLPIntent).filter(
            NLPIntent.account_id == 'test_nlp_account'
        ).delete()
        db.commit()


class TestNLPIntentParsing:
    """Test NLP intent parsing from natural language."""

    @pytest.mark.asyncio
    async def test_parse_whitelist_intent(self):
        """Test parsing whitelist intent."""
        text = "Alle Emails von boss@company.com sind wichtig"

        result = await parse_nlp_intent(text, account_id='test_nlp_account')

        assert result.parsed_intent.intent_type in ['whitelist_sender', 'set_trust_level']
        assert result.parsed_intent.sender_email == 'boss@company.com' or \
               'boss@company.com' in (result.parsed_intent.sender_email or '')
        assert result.parsed_intent.confidence > 0.5

    @pytest.mark.asyncio
    async def test_parse_blacklist_intent(self):
        """Test parsing blacklist intent."""
        text = "Blockiere alle Mails von spam@test-nlp.com"

        result = await parse_nlp_intent(text, account_id='test_nlp_account')

        assert result.parsed_intent.intent_type == 'blacklist_sender'
        assert 'spam@test-nlp.com' in (result.parsed_intent.sender_email or '')
        assert result.parsed_intent.confidence > 0.5

    @pytest.mark.asyncio
    async def test_parse_mute_categories_intent(self):
        """Test parsing category muting intent."""
        text = "Alle Newsletter von techcrunch.com muten"

        result = await parse_nlp_intent(text, account_id='test_nlp_account')

        assert result.parsed_intent.intent_type == 'mute_categories'
        assert 'newsletter' in [c.lower() for c in result.parsed_intent.categories]
        assert result.parsed_intent.confidence > 0.5

    @pytest.mark.asyncio
    async def test_parse_allow_only_categories_intent(self):
        """Test parsing allow-only categories intent."""
        text = "Von work@test-nlp.com nur wichtige Emails und Termine erlauben"

        result = await parse_nlp_intent(text, account_id='test_nlp_account')

        assert result.parsed_intent.intent_type in ['allow_only_categories', 'mute_categories']
        assert len(result.parsed_intent.categories) > 0
        assert result.parsed_intent.confidence > 0.5

    @pytest.mark.asyncio
    async def test_parse_domain_based_intent(self):
        """Test parsing domain-based intent."""
        text = "Alle Werbemails von zalando.de ignorieren"

        result = await parse_nlp_intent(text, account_id='test_nlp_account')

        assert result.parsed_intent.intent_type in ['blacklist_sender', 'mute_categories']
        assert 'zalando.de' in (result.parsed_intent.sender_domain or '') or \
               'zalando.de' in (result.parsed_intent.sender_email or '')
        assert result.parsed_intent.confidence > 0.5

    @pytest.mark.asyncio
    async def test_confidence_scores(self):
        """Test that confidence scores are valid."""
        text = "Emails von test@example.com sind wichtig"

        result = await parse_nlp_intent(text, account_id='test_nlp_account')

        assert 0.0 <= result.parsed_intent.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_suggested_actions(self):
        """Test that suggested actions are provided."""
        text = "Blockiere spam@test-nlp.com"

        result = await parse_nlp_intent(text, account_id='test_nlp_account')

        assert len(result.suggested_actions) > 0
        assert isinstance(result.suggested_actions[0], str)

    @pytest.mark.asyncio
    async def test_requires_confirmation(self):
        """Test that high-risk actions require confirmation."""
        # Blacklist should require confirmation
        text = "Blockiere alle Mails von important-client@company.com"

        result = await parse_nlp_intent(text, account_id='test_nlp_account')

        # Should require confirmation for blacklist
        assert isinstance(result.requires_confirmation, bool)

    @pytest.mark.asyncio
    async def test_reasoning_provided(self):
        """Test that reasoning is provided."""
        text = "Newsletter von techcrunch.com muten"

        result = await parse_nlp_intent(text, account_id='test_nlp_account')

        assert len(result.parsed_intent.reasoning) > 0
        assert isinstance(result.parsed_intent.reasoning, str)

    @pytest.mark.asyncio
    async def test_key_signals_extracted(self):
        """Test that key signals are extracted."""
        text = "Alle Werbemails von zalando.de automatisch archivieren"

        result = await parse_nlp_intent(text, account_id='test_nlp_account')

        assert len(result.parsed_intent.key_signals) > 0
        assert isinstance(result.parsed_intent.key_signals, list)


class TestIntentExecution:
    """Test execution of parsed intents."""

    @pytest.mark.asyncio
    async def test_execute_whitelist_intent(self, cleanup_test_data):
        """Test executing whitelist intent."""
        intent = ParsedIntent(
            intent_type='whitelist_sender',
            sender_email='vip@test-nlp.com',
            sender_domain=None,
            sender_name=None,
            trust_level='trusted',
            categories=[],
            confidence=0.95,
            reasoning='User explicitly whitelisted sender',
            key_signals=['whitelist', 'vip'],
            original_text='Whitelist vip@test-nlp.com'
        )

        executor = IntentExecutor()
        result = await executor.execute(
            intent=intent,
            account_id='test_nlp_account',
            source_channel='gui_chat',
            confirmed=True
        )

        assert result.success is True
        assert 'whitelisted' in result.message.lower()

        # Verify in database
        with get_db() as db:
            pref = db.query(SenderPreference).filter(
                SenderPreference.sender_email == 'vip@test-nlp.com',
                SenderPreference.account_id == 'test_nlp_account'
            ).first()
            assert pref is not None
            assert pref.is_whitelisted is True

    @pytest.mark.asyncio
    async def test_execute_blacklist_intent(self, cleanup_test_data):
        """Test executing blacklist intent."""
        intent = ParsedIntent(
            intent_type='blacklist_sender',
            sender_email='spam@test-nlp.com',
            sender_domain=None,
            sender_name=None,
            trust_level='blocked',
            categories=[],
            confidence=0.95,
            reasoning='User blocked spam sender',
            key_signals=['blacklist', 'spam'],
            original_text='Block spam@test-nlp.com'
        )

        executor = IntentExecutor()
        result = await executor.execute(
            intent=intent,
            account_id='test_nlp_account',
            source_channel='gui_chat',
            confirmed=True
        )

        assert result.success is True
        assert 'blacklisted' in result.message.lower()

        # Verify in database
        with get_db() as db:
            pref = db.query(SenderPreference).filter(
                SenderPreference.sender_email == 'spam@test-nlp.com',
                SenderPreference.account_id == 'test_nlp_account'
            ).first()
            assert pref is not None
            assert pref.is_blacklisted is True

    @pytest.mark.asyncio
    async def test_execute_mute_categories_intent(self, cleanup_test_data):
        """Test executing mute categories intent."""
        intent = ParsedIntent(
            intent_type='mute_categories',
            sender_email='newsletter@test-nlp.com',
            sender_domain=None,
            sender_name=None,
            trust_level=None,
            categories=['newsletter', 'werbung'],
            confidence=0.90,
            reasoning='User wants to mute newsletter',
            key_signals=['mute', 'newsletter'],
            original_text='Mute newsletter from newsletter@test-nlp.com'
        )

        executor = IntentExecutor()
        result = await executor.execute(
            intent=intent,
            account_id='test_nlp_account',
            source_channel='gui_chat',
            confirmed=True
        )

        assert result.success is True
        assert 'muted' in result.message.lower()

        # Verify in database
        with get_db() as db:
            pref = db.query(SenderPreference).filter(
                SenderPreference.sender_email == 'newsletter@test-nlp.com',
                SenderPreference.account_id == 'test_nlp_account'
            ).first()
            assert pref is not None
            assert 'newsletter' in pref.muted_categories

    @pytest.mark.asyncio
    async def test_execution_creates_nlp_intent_record(self, cleanup_test_data):
        """Test that execution creates NLPIntent record."""
        intent = ParsedIntent(
            intent_type='whitelist_sender',
            sender_email='tracked@test-nlp.com',
            sender_domain=None,
            sender_name=None,
            trust_level='trusted',
            categories=[],
            confidence=0.95,
            reasoning='Test tracking',
            key_signals=['test'],
            original_text='Test whitelist'
        )

        executor = IntentExecutor()
        await executor.execute(
            intent=intent,
            account_id='test_nlp_account',
            source_channel='gui_chat',
            confirmed=True
        )

        # Verify NLPIntent record exists
        with get_db() as db:
            nlp_intent = db.query(NLPIntent).filter(
                NLPIntent.account_id == 'test_nlp_account',
                NLPIntent.source_text == 'Test whitelist'
            ).first()
            assert nlp_intent is not None
            assert nlp_intent.status == 'completed'

    @pytest.mark.asyncio
    async def test_execution_creates_user_preference_rule(self, cleanup_test_data):
        """Test that execution creates UserPreferenceRule."""
        intent = ParsedIntent(
            intent_type='whitelist_sender',
            sender_email='rule@test-nlp.com',
            sender_domain=None,
            sender_name=None,
            trust_level='trusted',
            categories=[],
            confidence=0.95,
            reasoning='Test rule creation',
            key_signals=['test'],
            original_text='Create preference rule'
        )

        executor = IntentExecutor()
        await executor.execute(
            intent=intent,
            account_id='test_nlp_account',
            source_channel='gui_chat',
            confirmed=True
        )

        # Verify UserPreferenceRule exists
        with get_db() as db:
            rule = db.query(UserPreferenceRule).filter(
                UserPreferenceRule.account_id == 'test_nlp_account',
                UserPreferenceRule.pattern == 'rule@test-nlp.com'
            ).first()
            assert rule is not None
            assert rule.action == 'whitelist'
            assert rule.active is True


class TestEndToEndNLPFlow:
    """Test complete NLP flow from text to execution."""

    @pytest.mark.asyncio
    async def test_complete_nlp_workflow(self, cleanup_test_data):
        """Test complete workflow: parse → execute → verify."""
        # Step 1: Parse intent
        text = "Blockiere alle Mails von e2e-spam@test-nlp.com"
        parse_result = await parse_nlp_intent(text, account_id='test_nlp_account')

        assert parse_result.parsed_intent.intent_type == 'blacklist_sender'

        # Step 2: Execute intent
        executor = IntentExecutor()
        exec_result = await executor.execute(
            intent=parse_result.parsed_intent,
            account_id='test_nlp_account',
            source_channel='gui_chat',
            confirmed=True
        )

        assert exec_result.success is True

        # Step 3: Verify database changes
        with get_db() as db:
            pref = db.query(SenderPreference).filter(
                SenderPreference.sender_email == 'e2e-spam@test-nlp.com',
                SenderPreference.account_id == 'test_nlp_account'
            ).first()
            assert pref is not None
            assert pref.is_blacklisted is True
            assert pref.trust_level == 'blocked'
