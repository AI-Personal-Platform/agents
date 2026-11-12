"""The agent endpoint runs the Vercel AI input it receives."""

import json
from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, DeltaToolCalls, FunctionModel
from pydantic_ai.ui.vercel_ai.request_types import SubmitMessage

from app.agents import assistant
from app.api.routes import agent as agent_routes
from app.core.config import Settings
from tests.helpers.agent_api import user_message


@pytest.fixture
def configured_agent(test_agents: None, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(opencode_api_key="test", opencode_base_url="http://provider.test")
    monkeypatch.setattr(agent_routes, "settings", settings)


def test_run_sends_all_input_messages_to_the_model(
    api_client: TestClient,
    configured_agent: None,
    run_input: SubmitMessage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts: list[str] = []

    async def model(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator[str]:
        for message in messages:
            if isinstance(message, ModelRequest):
                for part in message.parts:
                    if isinstance(part, UserPromptPart) and isinstance(part.content, str):
                        prompts.append(part.content)
        yield json.dumps({"message": "Hi again."})

    monkeypatch.setattr(assistant, "get_agent_model", lambda: FunctionModel(stream_function=model))
    run_input.messages = [user_message("Hello"), *run_input.messages]

    response = api_client.post(
        "/agents/assistant",
        json=run_input.model_dump(mode="json", by_alias=True, exclude_none=True),
    )

    assert response.status_code == 200
    assert prompts == ["Hello", "Say hello in one short sentence."]


def test_run_rejects_non_json_requests(
    api_client: TestClient, configured_agent: None, run_input: SubmitMessage
) -> None:
    response = api_client.post(
        "/agents/assistant",
        content=run_input.model_dump_json(by_alias=True, exclude_none=True),
        headers={"content-type": "text/plain"},
    )
    assert response.status_code == 415


def test_run_stops_at_the_request_limit(
    api_client: TestClient,
    run_input: SubmitMessage,
    test_agents: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        opencode_api_key="test", opencode_base_url="http://provider.test", agent_request_limit=1
    )
    monkeypatch.setattr(agent_routes, "settings", settings)

    async def model(
        messages: list[ModelMessage], info: AgentInfo
    ) -> AsyncIterator[str | DeltaToolCalls]:
        if info.function_tools:
            yield {0: DeltaToolCall(name="summarize", json_args='{"text": "Some text."}')}
        else:
            yield "A summary."

    def summary(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart("A summary.")])

    monkeypatch.setattr(
        assistant,
        "get_agent_model",
        lambda: FunctionModel(summary, stream_function=model),
    )

    response = api_client.post(
        "/agents/assistant",
        json=run_input.model_dump(mode="json", by_alias=True, exclude_none=True),
    )

    assert response.status_code == 200
    assert '"type":"error"' in response.text
    assert "request_limit" in response.text


def test_empty_settings_values_use_the_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_MODEL", "")
    monkeypatch.setenv("AGENT_REQUEST_LIMIT", "")

    settings = Settings()

    assert settings.agent_model == Settings.model_fields["agent_model"].default
    assert settings.usage_limits.request_limit == 20
