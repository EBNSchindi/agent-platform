"""
Email Module Definition
Registers email agents with the platform.
"""

from agent_platform.core.registry import get_registry
from modules.email.agents.classifier import create_classifier_agent
from modules.email.agents.responder import create_responder_orchestrator


def register_email_module():
    """
    Register email module with the platform registry.
    """
    registry = get_registry()

    # Register module
    registry.register_module(
        name="email",
        version="1.0.0",
        description="Email inbox automation with classification, draft generation, and backup"
    )

    # Register Classifier Agent
    classifier = create_classifier_agent()
    registry.register_agent(
        module_name="email",
        agent_name="classifier",
        agent_instance=classifier,
        agent_type="classifier",
        description="Classifies emails as spam, important, normal, or auto-reply candidates",
        capabilities=["email_classification", "spam_detection", "urgency_assessment"]
    )

    # Register Responder Agent
    responder = create_responder_orchestrator()
    registry.register_agent(
        module_name="email",
        agent_name="responder",
        agent_instance=responder,
        agent_type="responder",
        description="Generates email response drafts with appropriate tone",
        capabilities=["email_response", "draft_generation", "tone_selection"]
    )

    print("✅ Email module registered successfully")
    return registry


if __name__ == "__main__":
    # Test module registration
    registry = register_email_module()
    registry.print_summary()
