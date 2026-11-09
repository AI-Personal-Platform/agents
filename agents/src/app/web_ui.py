"""Development chat UI from Pydantic AI's `Agent.to_web()`, served apart from the API."""

from app.agents.base import AgentDeps
from app.agents.personal import get_personal_agent

app = get_personal_agent().to_web(deps=AgentDeps(chat_id="web-ui"))
