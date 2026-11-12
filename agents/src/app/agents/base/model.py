from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic_ai import ModelSettings, RunContext
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.providers.openai import OpenAIProvider

from app.core.config import get_settings

AGENTS_DIR = Path(__file__).resolve().parents[1]


@dataclass
class AgentDeps:
    """Run dependencies shared with tools and forwarded to every subagent run."""

    conversation_id: str


def agent_model_settings(ctx: RunContext[AgentDeps]) -> ModelSettings:
    """Build provider headers from dependencies forwarded to every subagent run."""
    return {
        "extra_headers": {
            "User-Agent": "ai-agent-platform/0.1.0",
            "x-opencode-session": ctx.deps.conversation_id,
        }
    }


@lru_cache
def get_agent_model() -> Model:
    """Build the model for `MODEL_PROVIDER`: `opencode` (OpenAI Responses API) or `ollama`."""
    settings = get_settings()

    if settings.model_provider == "ollama":
        ollama_provider = OllamaProvider(base_url=settings.ollama_base_url)
        return OpenAIChatModel(settings.agent_model, provider=ollama_provider)

    opencode_provider = OpenAIProvider(
        api_key=settings.opencode_api_key,
        base_url=settings.opencode_base_url,
    )
    return OpenAIResponsesModel(settings.agent_model, provider=opencode_provider)
