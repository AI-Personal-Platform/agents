"""Tool metadata, deferred loading, toolset instructions, and approval, without a provider."""

from pydantic_ai import DeferredToolRequests, FunctionToolset
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.agents.base import AgentDeps, BaseAgent

feature_tools = FunctionToolset[AgentDeps](instructions="Use the archive tools only for archives.")


@feature_tools.tool_plain(metadata={"label": "Archive"}, defer_loading=True)
def find_archive(name: str) -> str:
    """Find an archive by name."""
    return name


@feature_tools.tool_plain(metadata={"label": "Mailer"}, requires_approval=True)
def send_mail(to: str) -> str:
    """Send a mail."""
    return to


async def test_deferred_tools_are_hidden_and_toolset_instructions_are_sent(
    test_agents: None,
) -> None:
    agent = BaseAgent[AgentDeps, str](
        deps_type=AgentDeps, name="test", skills=[], toolsets=[feature_tools]
    )
    seen: list[AgentInfo] = []

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen.append(info)
        return ModelResponse(parts=[TextPart("ok")])

    with agent.override(model=FunctionModel(model)):
        await agent.run("Hi", deps=AgentDeps(chat_id="t"))

    names = {tool.name for tool in seen[0].function_tools}
    assert "find_archive" not in names
    assert "send_mail" in names
    assert "Use the archive tools only for archives." in (seen[0].instructions or "")


async def test_approval_tool_ends_the_run_with_a_deferred_request(test_agents: None) -> None:
    agent = BaseAgent[AgentDeps, str | DeferredToolRequests](
        deps_type=AgentDeps,
        name="test",
        skills=[],
        toolsets=[feature_tools],
        output_type=[str, DeferredToolRequests],
    )

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[ToolCallPart("send_mail", {"to": "a@b.c"})])

    with agent.override(model=FunctionModel(model)):
        result = await agent.run("Mail a@b.c", deps=AgentDeps(chat_id="t"))

    assert isinstance(result.output, DeferredToolRequests)
    assert [call.tool_name for call in result.output.approvals] == ["send_mail"]
