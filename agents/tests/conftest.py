import os
from collections.abc import Iterator
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic_ai.models.test import TestModel
from pydantic_ai.ui.vercel_ai.request_types import SubmitMessage

from app.agents import assistant, personal
from app.agents.base import agent as base_agent
from app.main import app
from tests.helpers.agent_api import user_message


@pytest.fixture
def run_input() -> SubmitMessage:
    return SubmitMessage(
        id=str(uuid4()), messages=[user_message("Say hello in one short sentence.")]
    )


@pytest.fixture
def test_agents(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Build cached agents on TestModel; tests override the model they exercise."""
    monkeypatch.setattr(base_agent, "get_agent_model", TestModel)
    assistant.get_assistant_agent.cache_clear()
    personal.get_personal_agent.cache_clear()
    yield
    assistant.get_assistant_agent.cache_clear()
    personal.get_personal_agent.cache_clear()


@pytest.fixture
def api_client() -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


@pytest.fixture
def agent_api_client() -> Iterator[httpx.Client]:
    base_url = os.environ.get("AGENT_API_URL")
    if not base_url:
        pytest.skip("Set AGENT_API_URL to test the running agents service and real model provider.")
    with httpx.Client(base_url=base_url, timeout=120) as client:
        yield client
