"""Coordinator agent system prompt - modular structure."""

from llm.prompts.coordinator.base import BASE_PROMPT
from llm.prompts.coordinator.element_discovery import ELEMENT_DISCOVERY_SECTION
from llm.prompts.coordinator.error_recovery import ERROR_RECOVERY_SECTION
from llm.prompts.coordinator.security import SECURITY_SECTION
from llm.prompts.coordinator.interactions import INTERACTIONS_SECTION


def get_coordinator_prompt() -> str:
    """Assemble the complete coordinator system prompt from modules.

    Returns:
        Complete system prompt for the coordinator agent
    """
    return "\n\n".join([
        BASE_PROMPT,
        ELEMENT_DISCOVERY_SECTION,
        ERROR_RECOVERY_SECTION,
        SECURITY_SECTION,
        INTERACTIONS_SECTION,
    ])


__all__ = ["get_coordinator_prompt"]
