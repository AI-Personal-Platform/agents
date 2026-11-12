"""The agent endpoint offers the agent's tools and rejects unknown agents."""

import json
from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.ui.vercel_ai.request_types import SubmitMessage

from app.agents import assistant
from app.api.routes import agent as agent_routes
from app.core.config import Settings
from tests.helpers.agent_api import assert_agent_reply, parse_events


@pytest.fixture
def configured_tools(test_agents: None, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        opencode_api_key="test",
        opencode_base_url="http://provider.test",
    )
    monkeypatch.setattr(agent_routes, "settings", settings)


def test_run_offers_the_agent_tools(
    api_client: TestClient,
    configured_tools: None,
    run_input: SubmitMessage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def model(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator[str]:
        names = sorted(tool.name for tool in info.function_tools)
        yield json.dumps({"message": json.dumps(names)})

    monkeypatch.setattr(assistant, "get_agent_model", lambda: FunctionModel(stream_function=model))

    response = api_client.post(
        "/agents/assistant",
        json=run_input.model_dump(mode="json", by_alias=True, exclude_none=True),
    )

    assert response.status_code == 200
    events = parse_events(response.text.splitlines())
    reply = assert_agent_reply(events)
    assert json.loads(reply.message) == ["summarize"]


def test_unknown_agent_returns_404(
    api_client: TestClient, configured_tools: None, run_input: SubmitMessage
) -> None:
    response = api_client.post(
        "/agents/missing",
        json=run_input.model_dump(mode="json", by_alias=True, exclude_none=True),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown agent: missing."}
