# AI Personal Platform

A personal AI platform with agent chat and configurable tools. Built with FastAPI/Pydantic AI.

Built using my own knowledge and AI assistance for code, design, and documentation.

The service runs agents over the Vercel AI SDK UI message stream protocol (`VercelAIAdapter`, SDK v6). It is stateless: the client sends the full message history on each run.

## Quick start

Install [mise](https://mise.jdx.dev/) and Docker Compose, then run from the project root:

```bash
cp .env.example .env
mise trust
mise install
```

Set `OPENCODE_API_KEY` in `.env`. The example already provides the URLs needed for Docker.

With Docker:

```bash
mise local
```

Or natively, without Docker:

```bash
mise setup
mise dev
```

Both read the root `.env`. Open <http://localhost:8000/docs> for interactive API documentation. `mise dev` defaults `CORS_ORIGINS` to `http://localhost:3000,tauri://localhost` when it is not set in your shell.

## Agent configuration

- **Agents:** Each agent is a module in [agents/src/app/agents](agents/src/app/agents) that builds a `BaseAgent` with its `name`, `description`, and `instructions`, as [assistant.py](agents/src/app/agents/assistant.py) does. Its `name` is the agent ID. Register it in [agents/src/app/agents/__init__.py](agents/src/app/agents/__init__.py).
- **Web UI (optional):** `mise web-ui` serves Pydantic AI's chat UI for the personal agent at http://127.0.0.1:8001, using the root `.env`. It is a separate app in [web_ui.py](agents/src/app/web_ui.py); delete that file and the `web-ui` task in `mise.toml` to remove it.
- **Model:** `MODEL_PROVIDER` is `opencode` (default) or `ollama`, and `AGENT_MODEL` names the model; its default is in [config.py](agents/src/app/core/config.py). For Ollama, also set `OLLAMA_BASE_URL`.
- **Limits:** each run stops after `AGENT_REQUEST_LIMIT` model requests (default 20) or `AGENT_TOTAL_TOKENS_LIMIT` tokens (default 200000), counting the summarize tool's own request.
- **CORS:** `CORS_ORIGINS` lists the browser origins allowed to call the API, as a JSON list or comma-separated values.

## API

| Method | Path                         | Purpose                                  |
| ------ | ---------------------------- | ---------------------------------------- |
| GET    | `/`                          | Redirect to the API docs at `/docs`      |
| GET    | `/health`                    | Check process health                     |
| POST   | `/agents/{agent_id}`         | Run an agent and stream Vercel AI chunks |

## Tracing

Set `LOGFIRE_TOKEN` in `.env` to your project's write token to enable optional tracing for FastAPI, Pydantic AI, and outgoing HTTP requests. Leave it empty to disable cloud export. Restart the service afterwards, and rebuild the agents container for Docker.

`LOGFIRE_ENVIRONMENT` labels the environment. Model prompts, replies, and tool content are excluded by default; set `LOGFIRE_INCLUDE_CONTENT=true` to capture them. View requests and model activity in your Logfire project's Live view.

## Useful commands

Run these from the repository root:

| Command | Purpose |
| --- | --- |
| `mise local` | Build and start the Docker stack |
| `mise ps` | Show service status |
| `mise down` | Stop the stack and keep its volumes |
| `mise logs` | Follow the agents container logs |
| `mise setup` | Install dependencies for native development and checks |
| `mise dev` | Run the agents service natively without Docker, with reload |
| `mise check` | Run lint, format check, typecheck, and tests |
| `mise test` | Run pytest; skips the live test without `AGENT_API_URL` |
| `mise test-agent` | Run the live model test |

See [mise.toml](mise.toml) for all tasks.

## Live test

With the agents service running, export its host-accessible URL:

```bash
export AGENT_API_URL=http://127.0.0.1:8000
mise test-agent
```

The test sends one real model request and checks matching thread/run IDs, the structured response, and successful completion.

The [Agents workflow](.github/workflows/agents.yml) runs this test on relevant pull requests and manual dispatches. It requires the `OPENCODE_API_KEY` repository secret.
