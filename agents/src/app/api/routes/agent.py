"""Agent endpoint configuration and request validation."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from pydantic_ai import Agent
from pydantic_ai.ui.vercel_ai import VercelAIAdapter
from starlette.requests import Request
from starlette.responses import Response

from app.agents import find_agent
from app.agents.base import AgentDeps
from app.core.config import get_settings

settings = get_settings()
router = APIRouter()


def get_agent(agent_id: str) -> Agent[Any, Any]:
    agent = find_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}.")
    if not settings.model_configured:
        raise HTTPException(
            status_code=503,
            detail=(
                "Set MODEL_PROVIDER, AGENT_MODEL, and the provider's API key and base URL "
                "to run agents."
            ),
        )
    return agent


AgentDep = Annotated[Agent[Any, Any], Depends(get_agent)]


@router.post("/agents/{agent_id}")
async def run_agent(agent: AgentDep, request: Request) -> Response:
    try:
        adapter = await VercelAIAdapter[Any, Any].from_request(request, agent=agent, sdk_version=6)
    except ValidationError as error:
        return Response(
            error.json(include_input=False), status_code=422, media_type="application/json"
        )
    conversation_id = adapter.run_input.id
    if not conversation_id:
        raise HTTPException(status_code=422, detail="id must not be empty.")

    deps = AgentDeps(conversation_id=conversation_id)
    stream = adapter.run_stream(deps=deps, usage_limits=settings.usage_limits)
    return adapter.streaming_response(stream)
