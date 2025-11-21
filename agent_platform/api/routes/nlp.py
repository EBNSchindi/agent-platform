"""
NLP Intent API Routes (Phase 6)

API endpoints for NLP-based preference management:
- Parse natural language text into structured intents
- Execute parsed intents
- Manage user preference rules
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent_platform.senders import parse_nlp_intent, IntentExecutor, ParsedIntent
from agent_platform.db.database import get_db
from agent_platform.db.models import UserPreferenceRule


router = APIRouter(prefix="/api/nlp", tags=["nlp"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class NLPParseRequest(BaseModel):
    """Request model for NLP intent parsing."""
    text: str
    account_id: str


class NLPExecuteRequest(BaseModel):
    """Request model for NLP intent execution."""
    parsed_intent: Dict[str, Any]  # ParsedIntent as dict
    account_id: str
    confirmed: bool = True


class RulesListResponse(BaseModel):
    """Response model for listing user preference rules."""
    rules: List[Dict[str, Any]]
    total: int


# ============================================================================
# ROUTES
# ============================================================================

@router.post("/parse")
async def parse_intent(request: NLPParseRequest):
    """
    Parse natural language text into structured intent.

    Example:
        POST /api/nlp/parse
        {
            "text": "Alle Werbemails von Zalando muten",
            "account_id": "gmail_1"
        }

    Returns:
        IntentParserResult with parsed intent and suggested actions
    """
    try:
        result = await parse_nlp_intent(
            text=request.text,
            account_id=request.account_id
        )

        return {
            "parsed_intent": {
                "intent_type": result.parsed_intent.intent_type,
                "sender_email": result.parsed_intent.sender_email,
                "sender_domain": result.parsed_intent.sender_domain,
                "sender_name": result.parsed_intent.sender_name,
                "trust_level": result.parsed_intent.trust_level,
                "categories": result.parsed_intent.categories,
                "preferred_primary_category": result.parsed_intent.preferred_primary_category,
                "confidence": result.parsed_intent.confidence,
                "reasoning": result.parsed_intent.reasoning,
                "key_signals": result.parsed_intent.key_signals,
                "original_text": result.parsed_intent.original_text
            },
            "suggested_actions": result.suggested_actions,
            "requires_confirmation": result.requires_confirmation
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse intent: {str(e)}")


@router.post("/execute")
async def execute_intent(request: NLPExecuteRequest):
    """
    Execute a parsed NLP intent.

    Example:
        POST /api/nlp/execute
        {
            "parsed_intent": { ... },
            "account_id": "gmail_1",
            "confirmed": true
        }

    Returns:
        Execution result with success status and message
    """
    try:
        # Convert dict to ParsedIntent
        parsed_intent = ParsedIntent(**request.parsed_intent)

        # Execute intent
        executor = IntentExecutor()
        result = await executor.execute(
            intent=parsed_intent,
            account_id=request.account_id,
            source_channel='gui_chat',
            confirmed=request.confirmed
        )

        return {
            "success": result.success,
            "message": result.message,
            "error": result.error
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute intent: {str(e)}")


@router.get("/rules")
async def list_user_preference_rules(account_id: str) -> RulesListResponse:
    """
    Get all user preference rules for an account.

    Example:
        GET /api/nlp/rules?account_id=gmail_1

    Returns:
        List of user preference rules
    """
    try:
        with get_db() as db:
            rules = db.query(UserPreferenceRule).filter(
                UserPreferenceRule.account_id == account_id
            ).order_by(UserPreferenceRule.created_at.desc()).all()

            rules_list = [
                {
                    "id": rule.id,
                    "rule_id": rule.rule_id,
                    "account_id": rule.account_id,
                    "pattern": rule.pattern,
                    "action": rule.action,
                    "active": rule.active,
                    "created_at": rule.created_at.isoformat(),
                    "created_via": rule.created_via,
                    "source_text": rule.source_text
                }
                for rule in rules
            ]

            return RulesListResponse(
                rules=rules_list,
                total=len(rules_list)
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch rules: {str(e)}")
