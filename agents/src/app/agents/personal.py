from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_ai import Agent, NativeOutput
from pydantic_ai.workspaces import LocalWorkspaceBackend
from pydantic_ai_harness import ArtifactScanner
from pydantic_ai_harness.skills import Skills

from app.agents.base import AGENTS_DIR, AgentDeps, agent_model_settings, get_agent_model


class PersonalResponse(BaseModel):
    message: str = Field(min_length=1, description="The personal agent response to the user.")


@lru_cache
def get_personal_agent() -> Agent[AgentDeps, PersonalResponse]:
    skills = Skills(
        "skills",
        include=None,
        workspace=LocalWorkspaceBackend(AGENTS_DIR),
        scanner=ArtifactScanner(),
    )
    return Agent[AgentDeps, PersonalResponse](
        get_agent_model(),
        name="personal",
        deps_type=AgentDeps,
        model_settings=agent_model_settings,
        description="Personal assistant for the user's own notes and tasks.",
        instructions=["You are a concise personal assistant for the user's notes and tasks."],
        output_type=NativeOutput(PersonalResponse),
        capabilities=[skills],
    )
