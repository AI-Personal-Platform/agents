"""The summarize tool makes one isolated model request on the assistant's model and budget."""

import json
from asyncio import gather

import pytest
from pydantic_ai import Agent, UsageLimitExceeded, UsageLimits
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.agents import assistant
from app.agents.base import AgentDeps
from app.agents.tools.summarize import summary_budget

SOURCE = "The project uses Python."


class FakeModel:
    """Plays the assistant (calls summarize, then answers) and the summarize request."""

    def __init__(self) -> None:
        self.summaries: list[tuple[str, str, dict[str, str]]] = []

    def __call__(self, messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        last = messages[-1]
        settings = info.model_settings or {}
        headers = dict(settings.get("extra_headers") or {})
        if isinstance(last, ModelRequest) and (last.instructions or "").startswith("Summarize"):
            assert len(messages) == 1
            prompt = last.parts[0]
            assert isinstance(prompt, UserPromptPart) and isinstance(prompt.content, str)
            self.summaries.append((prompt.content, last.instructions or "", headers))
            return ModelResponse(parts=[TextPart(f"Summary for {headers['x-opencode-session']}")])
        if isinstance(last.parts[-1], ToolReturnPart):
            summary = last.parts[-1].model_response_object()["summary"]
            return ModelResponse(parts=[TextPart(json.dumps({"message": summary}))])
        return ModelResponse(parts=[ToolCallPart("summarize", {"text": SOURCE}, "summary-1")])


@pytest.fixture
def fake_model() -> FakeModel:
    return FakeModel()


@pytest.fixture
def agent(test_agents: None, fake_model: FakeModel) -> Agent[AgentDeps, assistant.AgentResponse]:
    return assistant.get_assistant_agent()


async def test_summary_returns_in_parent_run(
    agent: Agent[AgentDeps, assistant.AgentResponse],
    fake_model: FakeModel,
) -> None:
    with agent.override(model=FunctionModel(fake_model)):
        result = await agent.run(
            "Summarize the project description.",
            deps=AgentDeps(conversation_id="thread-1"),
            usage_limits=UsageLimits(request_limit=3),
        )

    assert result.output.message == "Summary for thread-1"
    assert result.usage.requests == 3
    [(prompt, instructions, headers)] = fake_model.summaries
    assert prompt == SOURCE
    assert "Keep the summary within 4 words." in instructions
    assert headers == {"User-Agent": "ai-agent-platform/0.1.0", "x-opencode-session": "thread-1"}

    returns = [
        part
        for message in result.all_messages()
        for part in message.parts
        if isinstance(part, ToolReturnPart) and part.tool_name == "summarize"
    ]
    assert [part.model_response_object() for part in returns] == [
        {"summary": "Summary for thread-1"}
    ]


async def test_parent_request_limit_counts_the_summarize_request(
    agent: Agent[AgentDeps, assistant.AgentResponse], fake_model: FakeModel
) -> None:
    with agent.override(model=FunctionModel(fake_model)), pytest.raises(UsageLimitExceeded):
        await agent.run(
            "Summarize this.",
            deps=AgentDeps(conversation_id="thread-1"),
            usage_limits=UsageLimits(request_limit=2),
        )
    assert len(fake_model.summaries) == 1


async def test_concurrent_summaries_keep_their_own_session_headers(
    agent: Agent[AgentDeps, assistant.AgentResponse], fake_model: FakeModel
) -> None:
    with agent.override(model=FunctionModel(fake_model)):
        first, second = await gather(
            agent.run("Summarize this.", deps=AgentDeps(conversation_id="thread-1")),
            agent.run("Summarize this.", deps=AgentDeps(conversation_id="thread-2")),
        )
    assert first.output.message == "Summary for thread-1"
    assert second.output.message == "Summary for thread-2"


@pytest.mark.parametrize(("words", "limit"), [(4, 4), (40, 15), (400, 100)])
def test_summary_budget_scales_with_the_source(words: int, limit: int) -> None:
    budget = summary_budget(" ".join(["w"] * words))
    assert (budget.source_words, budget.max_summary_words) == (words, limit)


async def test_assistant_gets_the_summarizer_tool_and_spec_rules(test_agents: None) -> None:
    seen: list[AgentInfo] = []

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen.append(info)
        return ModelResponse(parts=[TextPart('{"message":"ok"}')])

    agent = assistant.get_assistant_agent()
    with agent.override(model=FunctionModel(model)):
        await agent.run("Hi", deps=AgentDeps(conversation_id="t"))

    assert [tool.name for tool in seen[0].function_tools] == ["summarize"]
    assert "Summarization requires the summarize tool" in (seen[0].instructions or "")
