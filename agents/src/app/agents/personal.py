from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_ai import NativeOutput

from app.agents.base import AgentDeps, BaseAgent


class PersonalResponse(BaseModel):
    message: str = Field(min_length=1, description="The personal agent response to the user.")


@lru_cache
def get_personal_agent() -> BaseAgent[AgentDeps, PersonalResponse]:
    return BaseAgent[AgentDeps, PersonalResponse](
        name="personal",
        deps_type=AgentDeps,
        skills=None,
        description="Personal assistant for the user's own notes and tasks.",
        instructions=["You are a concise personal assistant for the user's notes and tasks."],
        output_type=NativeOutput(PersonalResponse),
    )
