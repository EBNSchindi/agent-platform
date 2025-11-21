"""
Intent Executor (Phase 5)

Executes parsed NLP intents by:
- Creating UserPreferenceRule records
- Updating SenderPreference records
- Logging events

Usage:
    executor = IntentExecutor()
    result = await executor.execute(parsed_intent, account_id)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from agent_platform.db.database import get_db
from agent_platform.db.models import UserPreferenceRule, NLPIntent, SenderPreference
from agent_platform.senders.profile_service import SenderProfileService
from agent_platform.senders.nlp_intent_agent import ParsedIntent
from agent_platform.events import log_event, EventType


class IntentExecutionResult:
    """
    Result of executing an intent.
    """
    def __init__(
        self,
        success: bool,
        message: str,
        sender_preference: Optional[SenderPreference] = None,
        user_preference_rule: Optional[UserPreferenceRule] = None,
        nlp_intent_id: Optional[int] = None,
        error: Optional[str] = None
    ):
        self.success = success
        self.message = message
        self.sender_preference = sender_preference
        self.user_preference_rule = user_preference_rule
        self.nlp_intent_id = nlp_intent_id
        self.error = error


class IntentExecutor:
    """
    Executor for parsed NLP intents.

    Applies parsed intents to the system by:
    - Creating UserPreferenceRule records
    - Updating SenderPreference via SenderProfileService
    - Logging events
    """

    def __init__(self):
        """Initialize intent executor."""
        self.profile_service = SenderProfileService()

    async def execute(
        self,
        intent: ParsedIntent,
        account_id: str,
        source_channel: str = 'gui_chat',
        confirmed: bool = True
    ) -> IntentExecutionResult:
        """
        Execute a parsed intent.

        Args:
            intent: Parsed intent to execute
            account_id: Account ID
            source_channel: Channel where intent originated (gui_chat, voice_note, etc.)
            confirmed: Whether user has confirmed the action

        Returns:
            IntentExecutionResult with execution status
        """
        # Log NLP intent to database
        nlp_intent_id = self._log_nlp_intent(intent, account_id, source_channel, confirmed)

        try:
            # Determine sender email/domain
            sender_identifier = self._resolve_sender_identifier(intent)

            if not sender_identifier:
                return IntentExecutionResult(
                    success=False,
                    message="Sender konnte nicht identifiziert werden",
                    nlp_intent_id=nlp_intent_id,
                    error="No sender_email, sender_domain, or sender_name provided"
                )

            # Execute intent based on type
            if intent.intent_type == 'whitelist_sender':
                result = await self._execute_whitelist(intent, sender_identifier, account_id)

            elif intent.intent_type == 'blacklist_sender':
                result = await self._execute_blacklist(intent, sender_identifier, account_id)

            elif intent.intent_type == 'set_trust_level':
                result = await self._execute_set_trust_level(intent, sender_identifier, account_id)

            elif intent.intent_type == 'mute_categories':
                result = await self._execute_mute_categories(intent, sender_identifier, account_id)

            elif intent.intent_type == 'allow_only_categories':
                result = await self._execute_allow_only_categories(intent, sender_identifier, account_id)

            elif intent.intent_type == 'remove_from_whitelist':
                result = await self._execute_remove_from_whitelist(intent, sender_identifier, account_id)

            elif intent.intent_type == 'remove_from_blacklist':
                result = await self._execute_remove_from_blacklist(intent, sender_identifier, account_id)

            else:
                result = IntentExecutionResult(
                    success=False,
                    message=f"Intent-Typ '{intent.intent_type}' nicht unterstützt",
                    nlp_intent_id=nlp_intent_id,
                    error=f"Unknown intent type: {intent.intent_type}"
                )

            # Update NLP intent status
            self._update_nlp_intent_status(
                nlp_intent_id,
                status='completed' if result.success else 'failed'
            )

            # Log event
            log_event(
                event_type=EventType.USER_FEEDBACK if result.success else EventType.EMAIL_CLASSIFICATION_FAILED,
                account_id=account_id,
                email_id=None,
                payload={
                    'intent_type': intent.intent_type,
                    'sender': sender_identifier,
                    'success': result.success,
                    'message': result.message,
                    'nlp_intent_id': nlp_intent_id
                }
            )

            return result

        except Exception as e:
            # Update NLP intent status to failed
            self._update_nlp_intent_status(nlp_intent_id, status='failed')

            return IntentExecutionResult(
                success=False,
                message=f"Fehler bei Ausführung: {str(e)}",
                nlp_intent_id=nlp_intent_id,
                error=str(e)
            )

    # ========================================================================
    # INTENT EXECUTION METHODS
    # ========================================================================

    async def _execute_whitelist(
        self,
        intent: ParsedIntent,
        sender: str,
        account_id: str
    ) -> IntentExecutionResult:
        """Execute whitelist_sender intent."""
        pref = await self.profile_service.whitelist_sender(
            sender_email=sender,
            account_id=account_id,
            allowed_categories=intent.categories if intent.categories else None,
            preferred_primary=intent.preferred_primary_category
        )

        # Create UserPreferenceRule
        rule = self._create_user_preference_rule(
            account_id=account_id,
            applies_to='sender',
            pattern=sender,
            action='whitelist',
            source_text=intent.original_text
        )

        return IntentExecutionResult(
            success=True,
            message=f"✅ {sender} wurde auf die Whitelist gesetzt",
            sender_preference=pref,
            user_preference_rule=rule
        )

    async def _execute_blacklist(
        self,
        intent: ParsedIntent,
        sender: str,
        account_id: str
    ) -> IntentExecutionResult:
        """Execute blacklist_sender intent."""
        pref = await self.profile_service.blacklist_sender(
            sender_email=sender,
            account_id=account_id
        )

        # Create UserPreferenceRule
        rule = self._create_user_preference_rule(
            account_id=account_id,
            applies_to='sender',
            pattern=sender,
            action='blacklist',
            source_text=intent.original_text
        )

        return IntentExecutionResult(
            success=True,
            message=f"🚫 {sender} wurde auf die Blacklist gesetzt (alle Emails → Spam)",
            sender_preference=pref,
            user_preference_rule=rule
        )

    async def _execute_set_trust_level(
        self,
        intent: ParsedIntent,
        sender: str,
        account_id: str
    ) -> IntentExecutionResult:
        """Execute set_trust_level intent."""
        if not intent.trust_level:
            return IntentExecutionResult(
                success=False,
                message="Trust level nicht angegeben",
                error="trust_level is None"
            )

        pref = await self.profile_service.set_trust_level(
            sender_email=sender,
            account_id=account_id,
            trust_level=intent.trust_level
        )

        # Create UserPreferenceRule
        rule = self._create_user_preference_rule(
            account_id=account_id,
            applies_to='sender',
            pattern=sender,
            action=f'set_trust_level:{intent.trust_level}',
            source_text=intent.original_text
        )

        return IntentExecutionResult(
            success=True,
            message=f"✓ {sender} Vertrauensstufe → {intent.trust_level}",
            sender_preference=pref,
            user_preference_rule=rule
        )

    async def _execute_mute_categories(
        self,
        intent: ParsedIntent,
        sender: str,
        account_id: str
    ) -> IntentExecutionResult:
        """Execute mute_categories intent."""
        if not intent.categories:
            return IntentExecutionResult(
                success=False,
                message="Keine Kategorien angegeben",
                error="categories is empty"
            )

        pref = await self.profile_service.mute_categories(
            sender_email=sender,
            categories=intent.categories,
            account_id=account_id
        )

        # Create UserPreferenceRule
        rule = self._create_user_preference_rule(
            account_id=account_id,
            applies_to='sender',
            pattern=sender,
            action=f'mute_categories:{",".join(intent.categories)}',
            source_text=intent.original_text
        )

        return IntentExecutionResult(
            success=True,
            message=f"🔇 Kategorien gemuted für {sender}: {', '.join(intent.categories)}",
            sender_preference=pref,
            user_preference_rule=rule
        )

    async def _execute_allow_only_categories(
        self,
        intent: ParsedIntent,
        sender: str,
        account_id: str
    ) -> IntentExecutionResult:
        """Execute allow_only_categories intent."""
        if not intent.categories:
            return IntentExecutionResult(
                success=False,
                message="Keine Kategorien angegeben",
                error="categories is empty"
            )

        pref = await self.profile_service.allow_only_categories(
            sender_email=sender,
            categories=intent.categories,
            account_id=account_id
        )

        # Create UserPreferenceRule
        rule = self._create_user_preference_rule(
            account_id=account_id,
            applies_to='sender',
            pattern=sender,
            action=f'allow_only:{",".join(intent.categories)}',
            source_text=intent.original_text
        )

        return IntentExecutionResult(
            success=True,
            message=f"✓ Nur Kategorien erlaubt für {sender}: {', '.join(intent.categories)}",
            sender_preference=pref,
            user_preference_rule=rule
        )

    async def _execute_remove_from_whitelist(
        self,
        intent: ParsedIntent,
        sender: str,
        account_id: str
    ) -> IntentExecutionResult:
        """Execute remove_from_whitelist intent."""
        pref = await self.profile_service.remove_from_whitelist(
            sender_email=sender,
            account_id=account_id
        )

        # Create UserPreferenceRule
        rule = self._create_user_preference_rule(
            account_id=account_id,
            applies_to='sender',
            pattern=sender,
            action='remove_from_whitelist',
            source_text=intent.original_text
        )

        return IntentExecutionResult(
            success=True,
            message=f"↩️ {sender} von Whitelist entfernt (Vertrauensstufe → neutral)",
            sender_preference=pref,
            user_preference_rule=rule
        )

    async def _execute_remove_from_blacklist(
        self,
        intent: ParsedIntent,
        sender: str,
        account_id: str
    ) -> IntentExecutionResult:
        """Execute remove_from_blacklist intent."""
        pref = await self.profile_service.remove_from_blacklist(
            sender_email=sender,
            account_id=account_id
        )

        # Create UserPreferenceRule
        rule = self._create_user_preference_rule(
            account_id=account_id,
            applies_to='sender',
            pattern=sender,
            action='remove_from_blacklist',
            source_text=intent.original_text
        )

        return IntentExecutionResult(
            success=True,
            message=f"↩️ {sender} von Blacklist entfernt (entsperrt)",
            sender_preference=pref,
            user_preference_rule=rule
        )

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _resolve_sender_identifier(self, intent: ParsedIntent) -> Optional[str]:
        """
        Resolve sender identifier from intent.

        Priority:
        1. sender_email (specific email address)
        2. sender_domain (domain-level rule)
        3. sender_name (fallback - may need domain lookup)

        Args:
            intent: Parsed intent

        Returns:
            Sender identifier (email or domain) or None
        """
        if intent.sender_email:
            return intent.sender_email

        if intent.sender_domain:
            return intent.sender_domain

        if intent.sender_name:
            # For sender_name without domain, we'll use it as-is
            # In the future, we could add domain lookup logic
            return intent.sender_name

        return None

    def _log_nlp_intent(
        self,
        intent: ParsedIntent,
        account_id: str,
        source_channel: str,
        confirmed: bool
    ) -> int:
        """
        Log NLP intent to database.

        Args:
            intent: Parsed intent
            account_id: Account ID
            source_channel: Source channel
            confirmed: Whether confirmed

        Returns:
            NLP intent ID
        """
        with get_db() as db:
            nlp_intent = NLPIntent(
                account_id=account_id,
                source_text=intent.original_text,
                source_channel=source_channel,
                parsed_intent={
                    'intent_type': intent.intent_type,
                    'sender_email': intent.sender_email,
                    'sender_domain': intent.sender_domain,
                    'sender_name': intent.sender_name,
                    'trust_level': intent.trust_level,
                    'categories': intent.categories,
                    'preferred_primary_category': intent.preferred_primary_category,
                    'confidence': intent.confidence,
                    'reasoning': intent.reasoning
                },
                intent_type=intent.intent_type,
                confidence=intent.confidence,
                status='pending',
                user_confirmed=confirmed
            )
            db.add(nlp_intent)
            db.commit()
            db.refresh(nlp_intent)
            return nlp_intent.id

    def _update_nlp_intent_status(self, nlp_intent_id: int, status: str):
        """Update NLP intent status."""
        with get_db() as db:
            nlp_intent = db.query(NLPIntent).filter(
                NLPIntent.id == nlp_intent_id
            ).first()

            if nlp_intent:
                nlp_intent.status = status
                if status == 'completed':
                    nlp_intent.executed_at = datetime.utcnow()
                db.commit()

    def _create_user_preference_rule(
        self,
        account_id: str,
        applies_to: str,
        pattern: str,
        action: str,
        source_text: str
    ) -> UserPreferenceRule:
        """
        Create UserPreferenceRule record.

        Args:
            account_id: Account ID
            applies_to: What the rule applies to (sender, category, etc.)
            pattern: Pattern to match (email, domain, etc.)
            action: Action to take
            source_text: Original NLP input

        Returns:
            Created UserPreferenceRule
        """
        with get_db() as db:
            rule = UserPreferenceRule(
                account_id=account_id,
                applies_to=applies_to,
                pattern=pattern,
                action=action,
                created_via='nlp_intent',
                source_text=source_text,
                active=True
            )
            db.add(rule)
            db.commit()
            db.refresh(rule)
            db.expunge(rule)  # Allow access outside session
            return rule
