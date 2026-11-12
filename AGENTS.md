# Repository Guidelines

## Project Structure

- FastAPI in `agents/src/app/`: `api/` for routes, `agents/` for agents, `core/` for settings and telemetry. Agents service tests live in `agents/tests/`.
  - `agents/base/` holds `AgentDeps`, the shared provider model (`get_agent_model`, `agent_model_settings`), and `AGENTS_DIR`. There is no base agent class: every agent is a plain Pydantic AI `Agent[DepsT, OutputT]` (deps that are `AgentDeps` or a subclass, any output type; the registry and routes accept `Agent[Any, Any]`) built in a module under `agents/` (such as `assistant.py`) that passes `get_agent_model()`, `deps_type`, `model_settings=agent_model_settings`, `name`, `description`, `instructions`, its `Skills` capability, and any `toolsets` and `output_type`.
  - `agents/tools/` holds one module per toolset, such as `summarize.py` with its tool, result models, and instruction template. Use native Pydantic AI tool options instead of custom wrappers: `metadata={"label": ...}` for the label, `defer_loading=True` to hide a tool until tool search finds it, `requires_approval=True` for user approval (the agent must then include `DeferredToolRequests` in its `output_type`), and `FunctionToolset(instructions=...)` for toolset prompt text. Rules for when to use a tool go in the agent's `instructions`. There is no per-run tool selection.
  - `agents/skills/` holds Agent Skills as `<name>/SKILL.md`. Each agent passes its own `Skills("skills", include=..., workspace=LocalWorkspaceBackend(AGENTS_DIR), scanner=ArtifactScanner())` capability from `pydantic-ai-harness` in `capabilities`: `include=None` for every skill, a list of skill names, or `[]` for none; the `ArtifactScanner` leaves out skills that look like prompt injection, and the model loads one with `load_capability`.
  - The summarize tool is a single direct model request, not a sub-agent; if a real sub-agent is added later, use Pydantic AI agent delegation via a tool that calls `child.run(..., deps=ctx.deps, usage=ctx.usage)`.
  - Add an agent by creating a module in `agents/` and an entry in the `AGENTS` registry in `agents/__init__.py`. Avoid abstractions that serve a single agent.
- The agents service does not call a backend.
- Root `compose.yaml`, `mise.toml`, `.env.example`, and `README.md` coordinate development. Preserve official scaffold output unless integration requires a change.
- GitHub Actions workflows in `.github/workflows/` and their shell scripts in `.github/workflows/scripts/`. The `Agents` workflow calls `test_agents.sh` to start Uvicorn, wait for health, run the live API test, and stop the server.

## Service Boundaries

- The agents service does not use a database. Do not add database settings, drivers, connection helpers, or a database health endpoint.
- The assistant agent returns `AgentResponse` through `NativeOutput(AgentResponse)` with a required nonempty `message` field. Preserve this structured response contract in the live API test.

## Build, Test, and Development Commands

### Setup

- `mise trust` and `mise install` enable the versions declared in `mise.toml`; run once.
- `mise setup` installs the tools and the Python dependencies.

### Task layout

- The single root `mise.toml` contains shared tool versions, `setup` for installing all application dependencies, Docker commands, development, quality check, test and cleanup tasks, and GitHub/Git workflow tasks. There is no per-application `mise.toml`.
- Run every task with `mise <task>` from the root. The Python project (`pyproject.toml`, `uv.lock`, `.python-version`, `.venv`) lives at the root, and the code is in `agents/src` and `agents/tests`; tool paths in `pyproject.toml` and the mise tasks point there.
- `mise local` builds and starts the Docker stack, and `mise dev` runs the agents service natively without Docker. The agents tasks are `lint`, `lint-fix`, `format`, `format-check`, `typecheck`, `test`, `test-agent`, `check`, `logs`, `shell`, and `web-ui`.

### Docker

- Root `mise local` builds and starts the Docker stack; `mise ps` shows status, and `mise down` stops the stack while preserving volumes.
- `docker compose config` validates Compose configuration, and `docker compose up --build` builds and starts all services. Rebuild containers after dependency or Dockerfile changes.

### Cleanup

- `mise clean-cache` removes the application caches and the root `.ruff_cache/`, preserving installed dependencies and global package caches. `mise clean-deps` removes the application's dependency directory. `mise setup` reinstalls all application dependencies.

### GitHub and Git workflows

- `mise create-issue` selects a Markdown issue template by its frontmatter name and passes it to `gh issue create --template`; accept only `bug-report` and `feature-request` as selectors. Templates must be recognized on the default branch, and their names must be unique across Markdown templates and YAML forms.
- `mise create-issue-branch <number> --name <type>/<slug>` creates, links, and checks out an issue branch. It shares branch naming validation with `create-stack` in `scripts/lib/branch_name.sh`; use names such as `feat/api`, `docs/guide`, or `fix/login`.
- `mise create-pr` creates a pull request with `.github/pull_request_template.md`. `mise install-gh-stack` installs the `gh stack` extension. `mise create-stack` opens a menu of common stack actions and requires a clean working tree to initialize. Order branch names from the bottom layer to the top.

### Tool selection

- Mise selects Python, uv, and GitHub CLI from `mise.toml` while working in this repository. Use `mise x -- <command>` for direct tool commands, or enable shell activation to put the selected tools on `PATH` automatically when entering the repository.

## Coding Style & Naming Conventions

- Python uses Ruff, four-space indentation, snake_case names, and type annotations for application interfaces.
- Keep modules focused and configuration environment-based.

## Testing Guidelines

- Add agents service tests under `agents/tests/` with names such as `test_health.py`; test HTTP endpoints with the configured `httpx` client.
- Run relevant tests and lint/type checks before proposing changes; report only checks actually run.
- Live API test (`agents/tests/api/test_agent_api.py`): test through the real HTTP endpoint and configured model provider; do not replace it with a mocked agent or `TestModel`. Send a complete Vercel AI `submit-message` payload and verify a `start` chunk, streamed `text-delta` JSON validated with `AgentResponse.model_validate_json`, a nonempty `message`, a final `finish` chunk with `finishReason` `stop`, and no `error` chunks. Use separate assertions for independent conditions. Ordinary pytest runs skip this test when `AGENT_API_URL` is unset; `mise test-agent` requires an explicitly exported target and sends one real model request.
- The `Agents` workflow runs on relevant pull requests and manual dispatches, with no push trigger on `main`. It requires the `OPENCODE_API_KEY` repository secret and fails clearly when it is unavailable. Keep token permissions read-only and do not use `pull_request_target` to expose secrets to fork code.
- Distinguish local test results, skipped live tests, and workflow runs actually executed by GitHub Actions.

## Commit & Pull Request Guidelines

- Use a conventional commit type in each subject: `feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `perf:`, `test:`, `build:`, `ci:`, `chore:`, or `revert:`. An optional scope is allowed, as in `feat(api): add chat history`. The commit-message hook validates this format.
- Run relevant application lint and type checks with mise before proposing changes.
- Use the issue templates in `.github/ISSUE_TEMPLATE/` (bug report and feature request, both for the agents service) to track personal work and follow `.github/pull_request_template.md` when opening pull requests; its checklist lists the agents `check`, `test`, and `test-agent` commands.

## Security & Configuration

- Copy `.env.example` for local configuration; never commit real environment files or credentials.
- Keep internal URLs and credentials server-side.
- Keep runtime URLs in environment configuration and example values in `.env.example`.
- Agent requests require `OPENCODE_API_KEY` and `OPENCODE_BASE_URL` when `MODEL_PROVIDER=opencode`, or `OLLAMA_BASE_URL` when `MODEL_PROVIDER=ollama`.
- Compose reads service and container health-check URLs from the root environment; do not embed URL fallbacks in application code or Compose.
- Non-secret defaults, such as `AGENT_MODEL`, live only in `Settings` (`agents/src/app/core/config.py`). Compose passes `${VAR:-}` and `.env.example` leaves them empty; `Settings` ignores empty values, so they fall back to its defaults.
- Every API run uses `Settings.usage_limits`, set by `AGENT_REQUEST_LIMIT` and `AGENT_TOTAL_TOKENS_LIMIT`; a run that exceeds them streams an `error` chunk.
