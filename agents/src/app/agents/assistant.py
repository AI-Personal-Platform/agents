from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_ai import Agent, NativeOutput
from pydantic_ai.workspaces import LocalWorkspaceBackend
from pydantic_ai_harness import ArtifactScanner
from pydantic_ai_harness.skills import Skills

from app.agents.base import AGENTS_DIR, AgentDeps, agent_model_settings, get_agent_model
from app.agents.tools.summarize import summarize_toolset


class AgentResponse(BaseModel):
    message: str = Field(min_length=1, description="The assistant response to the user.")


@lru_cache
def get_assistant_agent() -> Agent[AgentDeps, AgentResponse]:
    skills = Skills(
        "skills",
        include=None,
        workspace=LocalWorkspaceBackend(AGENTS_DIR),
        scanner=ArtifactScanner(),
    )
    return Agent[AgentDeps, AgentResponse](
        get_agent_model(),
        name="assistant",
        deps_type=AgentDeps,
        model_settings=agent_model_settings,
        description="Concise assistant that summarizes text with its summarize tool.",
        instructions=[
            "You are a concise assistant. Answer general questions that need no tool directly.",
            "Summarization requires the summarize tool, passing the full source text unchanged. "
            "Use the returned summary in your response and never write a summary yourself.",
        ],
        output_type=NativeOutput(AgentResponse),
        toolsets=[summarize_toolset],
        capabilities=[skills],
    )
