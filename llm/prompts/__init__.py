"""System prompts for the coordinator and sub-agents.

This module provides a modular structure for AI agent prompts.
"""

from llm.prompts.coordinator import get_coordinator_prompt
from llm.prompts.sub_agents import (
    get_navigator_prompt,
    get_form_filler_prompt,
    get_data_reader_prompt,
)


def get_subagent_prompt(subagent_name: str) -> str:
    """Get the system prompt for a specific sub-agent.

    Args:
        subagent_name: Name of the sub-agent ('navigator', 'form_filler', or 'data_reader')

    Returns:
        System prompt string for the sub-agent

    Raises:
        ValueError: If subagent_name is unknown
    """
    prompts = {
        "navigator": get_navigator_prompt,
        "form_filler": get_form_filler_prompt,
        "data_reader": get_data_reader_prompt,
    }

    if subagent_name not in prompts:
        raise ValueError(f"Unknown sub-agent: {subagent_name}")

    return prompts[subagent_name]()


__all__ = [
    "get_coordinator_prompt",
    "get_subagent_prompt",
    "get_navigator_prompt",
    "get_form_filler_prompt",
    "get_data_reader_prompt",
]
