from collections.abc import Collection, Sequence
from pathlib import Path
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.workspaces import LocalWorkspaceBackend
from pydantic_ai_harness import ArtifactScanner
from pydantic_ai_harness.skills import Skills

from app.agents.base.model import AgentDeps, agent_model_settings, get_agent_model

AGENTS_DIR = Path(__file__).resolve().parents[1]


class BaseAgent[DepsT: AgentDeps, OutputT](Agent[DepsT, OutputT]):
    """Shared-model agent with its deps type and the skills it selects."""

    def __init__(
        self,
        *,
        deps_type: type[DepsT],
        skills: Collection[str] | None,
        capabilities: Sequence[AbstractCapability[DepsT]] = (),
        **kwargs: Any,
    ) -> None:
        self.skills = Skills(
            "skills",
            include=skills,
            workspace=LocalWorkspaceBackend(AGENTS_DIR),
            scanner=ArtifactScanner(),
        )
        super().__init__(
            get_agent_model(),
            deps_type=deps_type,
            model_settings=agent_model_settings,
            capabilities=[self.skills, *capabilities],
            **kwargs,
        )
