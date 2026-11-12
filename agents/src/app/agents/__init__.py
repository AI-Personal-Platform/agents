"""Pydantic AI agents and the registry that looks them up by name."""

from collections.abc import Callable
from typing import Any

from pydantic_ai import Agent

from .assistant import get_assistant_agent
from .personal import get_personal_agent

AGENTS: dict[str, Callable[[], Agent[Any, Any]]] = {
    "assistant": get_assistant_agent,
    "personal": get_personal_agent,
}


def find_agent(agent_id: str) -> Agent[Any, Any] | None:
    """Return the agent whose name is `agent_id`, or None when none is registered."""
    factory = AGENTS.get(agent_id)
    if factory is None:
        return None
    return factory()
