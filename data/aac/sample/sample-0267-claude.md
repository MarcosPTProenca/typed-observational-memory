# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Learning and experimentation repository for the **Microsoft Agent Framework (MAF)**. Contains a production-quality **PM Copilot** application and comprehensive MAF documentation/examples.

## Running the PM Copilot (`maf/`)

```bash
# Setup
cd maf
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in OPENAI_API_KEY at minimum

# Run modes
python app.py --console      # Interactive terminal
python app.py --server       # FastAPI server (Teams + local web chat + AG-UI)
python app.py --devui        # MAF Developer UI (visual debugging)
python app.py --copilotkit   # Alias for --server
```

The server exposes: `POST /api/local_chat`, `POST /api/messages` (Teams), `GET /chat` (web UI), `/copilotkit` (AG-UI endpoint).

`GRAPH_MODE=mock` (default) uses stub data; `GRAPH_MODE=live` requires Azure credentials for real MS Graph calls.

## CopilotKit Starter (`maf_copilotkit/`)

```bash
# Backend
cd maf_copilotkit/agent
uv venv && source .venv/bin/activate
uv pip install -e .
uvicorn server:app --reload --port 8000

# Frontend
cd maf_copilotkit/web
pnpm install && pnpm dev
```

## AG-UI Monorepo (`tmp-ag-ui/`)

```bash
cd tmp-ag-ui
pnpm install && pnpm build
pnpm test    # run tests
pnpm lint    # lint code
pnpm dev     # watch mode for SDKs
```

## Architecture

**Star-topology Handoff pattern:** A Triage agent routes to 5 specialist agents, each hands back to Triage when done.

- **Triage** (`maf/agents/triage.py`) - Central router, no tools, pure reasoning
- **Specialists** - SharePoint, Meetings, Calendar, Documents, Project Info agents
- **Orchestration** wired in `maf/orchestration/handoff_workflow.py` using `HandoffBuilder`
- **Tools** in `maf/tools/` use `<REDACTED_USER>(approval_mode="never_require")` decorator with `Annotated` params
- **Graph client** (`maf/tools/graph_client.py`) - Lazy singleton, mock/live mode based on `GRAPH_MODE`
- **Config** (`maf/config.py`) - `pydantic-settings` loading from `.env`
- **AG-UI bridge** (`maf/agui_endpoint.py`) - Stateless wrapper creating fresh workflow per request

Evaluation pattern examples live in `maf/agents/01_handoff/` through `05_magentic/`.

## Conventions

- New tools go in `maf/tools/`, new agents in `maf/agents/`
- New agents in the PM Copilot flow must be wired in `maf/orchestration/handoff_workflow.py`
- Never commit `.env` files or secrets
- Python 3.10+, PEP 8, `agent-framework==1.0.0rc4`
- Update `ANTIGRAVITY.md` if architectural changes are made
- See `ANTIGRAVITY.md` for MAF upgrade procedures