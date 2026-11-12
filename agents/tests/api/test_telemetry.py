"""Capture application traces in memory without exporting them or calling a real model."""

import json
from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from logfire.testing import CaptureLogfire
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.ui.vercel_ai.request_types import SubmitMessage

from app.agents import assistant
from app.api.routes import agent as agent_routes
from app.core.config import Settings
from tests.helpers.agent_api import user_message


def test_agent_requests_are_traced_without_prompt_content(
    capfire: CaptureLogfire,
    api_client: TestClient,
    test_agents: None,
    run_input: SubmitMessage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        agent_routes,
        "settings",
        Settings(opencode_api_key="test", opencode_base_url="http://provider.test"),
    )

    async def model(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator[str]:
        yield json.dumps({"message": "Traced reply."})

    monkeypatch.setattr(assistant, "get_agent_model", lambda: FunctionModel(stream_function=model))
    marker = "private-telemetry-test-prompt"
    run_input.messages = [user_message(marker)]

    response = api_client.post(
        "/agents/assistant",
        json=run_input.model_dump(mode="json", by_alias=True, exclude_none=True),
    )

    assert response.status_code == 200
    assert '"type":"finish"' in response.text
    assert '"type":"error"' not in response.text
    spans = capfire.exporter.exported_spans_as_dict(include_instrumentation_scope=True)
    assert any(span["name"] == "POST /agents/{agent_id}" for span in spans)
    assert any(span["instrumentation_scope"] == "pydantic-ai" for span in spans)
    assert marker not in json.dumps(spans, default=str)


def test_health_checks_are_excluded_from_server_traces(
    capfire: CaptureLogfire, api_client: TestClient
) -> None:
    response = api_client.get("/health")

    assert response.status_code == 200
    spans = capfire.exporter.exported_spans_as_dict()
    assert not any(span["name"] == "GET /health" for span in spans)
