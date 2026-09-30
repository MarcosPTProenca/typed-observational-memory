# Agent Marketplace Demo - Agent Instructions

## Project Overview

A 2D pixel-art desktop application that visualizes multi-agent systems in real-time. Built with Tauri + React + Three.js + TypeScript frontend, and Python FastAPI + LangGraph backend.

## Tech Stack

**Frontend (Web-First):**
- React 19 + TypeScript
- Vite (Build tool & dev server)
- Three.js + React Three Fiber (2D pixel art rendering)
- shadcn/ui (UI components)

**Backend:**
- Python FastAPI (Async HTTP server)
- LangGraph (Agent orchestration - state-of-the-art)
- OpenAI GPT-4o-mini (LLM, can switch to local)

**Optional Later:** Tauri (for standalone desktop wrapper)

## Agent Roles & Council

All agents work on the codebase. Prefix your session with a Council role:

- **[Council Role: Architect]** - Design architecture, integration points, identify risks
- **[Council Role: Analyst]** - Validate requirements, identify gaps, plan implementation
- **[Council Role: Implementer]** - Write code, implement features, fix bugs
- **[Council Role: Reviewer]** - Review code for quality, bugs, performance

All agents are fungible generalists. Roles are for coordination, not expertise.

## Project Structure

```
agent-marketplace-demo/
├── src/                    # React + Three.js frontend
│   ├── components/         # React components
│   ├── hooks/              # Custom React hooks
│   └── lib/                # Utilities
├── agent-backend/          # Python FastAPI + LangGraph
│   ├── agents/             # LangGraph agent graphs
│   └── models/             # Pydantic schemas
├── assets/
│   └── sprites/            # Pixel art assets
└── docs/
```

## Work Location

**This project is at:** `<REDACTED_USERPATH>/agent-marketplace-demo/`

ALWAYS use `bd` (beads) from this project directory:
```bash
cd <REDACTED_USERPATH>/agent-marketplace-demo
```

## Required Tools

Always check your Agent Mail for coordination.

### BV (Beads) - Task Selection

```bash
cd <REDACTED_USERPATH>/agent-marketplace-demo

# THE MEGA-COMMAND: Get best bead to work on
bv --robot-triage

# Just the top pick
bv --robot-next

# Get parallel execution tracks (for multiple agents)
bv --robot-plan

# Check for cycles (MUST FIX if found)
bv --robot-insights | jq '.Cycles'

# Find bottlenecks
bv --robot-insights | jq '.bottlenecks'
```

**CRITICAL:** Never run bare `bv` — it launches interactive TUI that blocks.

### File Reservations

Before editing files, reserve them:
```bash
file_reservation_paths \
  project_key="<REDACTED_USERPATH>/agent-marketplace-demo" \
  agent_name="YourAgentName" \
  paths=["src/components/AgentCanvas.tsx"] \
  ttl_seconds=3600 \
  exclusive=true \
  reason="bd-123"
```

After completing work:
```bash
release_file_reservations \
  project_key="<REDACTED_USERPATH>/agent-marketplace-demo" \
  agent_name="YourAgentName"
```

## Workflow

### 1. Session Start

1. Read this AGENTS.md file carefully
2. Read README.md
3. Register with Agent Mail
4. Introduce yourself to other agents
5. Check inbox for messages

### 2. Pick Next Bead

```bash
cd <REDACTED_USERPATH>/agent-marketplace-demo
bv --robot-next
```

Pick the bead you can usefully work on now.

### 3. Announce Work

Send Agent Mail message:
- Subject: `[bd-XXX] Starting task description`
- Thread ID: `bd-XXX`
- Mention files you're reserving
- Mark bead as `in_progress`

### 4. Implement

Write code following best practices:
- TypeScript strict mode
- React best practices (hooks, components)
- Three.js performance (instancing for many sprites)
- Python type hints (pydantic models)

### 5. Self-Review

After completing work:
```
Carefully read over all of the new code you just wrote with "fresh eyes" looking for any obvious bugs, errors, problems, issues, confusion, etc. Carefully fix anything you uncover. Use ultrathink.
```

Keep running this until you stop finding bugs.

### 6. Complete Bead

1. Update bead status to `done`
2. Release file reservations
3. Send Agent Mail: `[bd-XXX] Completed`
4. Respond to any messages

### 7. Cross-Review

Periodically review other agents' code:
```
Turn your attention to reviewing the code written by your fellow agents and check for any issues, bugs, errors, problems, inefficiencies, security problems, reliability issues, etc. and carefully diagnose their underlying root causes using first-principle analysis and then fix or revise them if necessary. Don't restrict yourself to the latest commits, cast a wider net and go super deep. Use ultrathink.
```

### 8. Commit

When you've completed a logical set of work:
```
Commit all changed files now in a series of logically connected groupings with super detailed commit messages for each and then push. Take your time to do it right. Don't edit the code at all. Don't commit obviously ephemeral files. Use ultrathink.
```

## Technical Guidelines

### TypeScript/React Frontend

- Use strict TypeScript (no `any`)
- Functional components with hooks
- React Three Fiber for Three.js integration
- `useFrame` hook for animations
- `useThree` hook for Three.js access
- shadcn/ui for UI components

### Three.js Guidelines

- Use `InstancedMesh` for 100+ identical sprites
- Sprite sheets for animations
- LOD (Level of Detail) for performance
- Frustum culling (automatic in Three.js)
- Pixel-perfect rendering: `renderer.setPixelRatio(1, 1)`

### Python Backend

- Use FastAPI for async API
- Pydantic for request/response validation
- LangGraph for agent orchestration
- Type hints everywhere
- Async/await for I/O operations

### LangGraph Guidelines

- State graph with nodes: `perceive`, `reason`, `act`
- TypedDict for state
- LLM via LangChain OpenAI
- Batch processing for multiple agents

## Quality Standards

- **No `any` types** - Use proper TypeScript types
- **No `console.log`** - Use proper logging
- **No hardcoded values** - Use constants/config
- **Type safety everywhere** - Python type hints + Pydantic
- **Error handling** - Try/catch, proper error messages
- **Performance** - Profile before optimizing
- **Tests** - Write tests for critical paths

## Commit Message Format

```
[Component] Brief description

Details:
- What changed
- Why changed
- Impact

Related beads: bd-XXX, bd-YYY
```

## Important Reminders

1. **Always work from `<REDACTED_USERPATH>/agent-marketplace-demo/`**
2. **Always reserve files before editing**
3. **Always check Agent Mail between tasks**
4. **Always self-review before marking bead done**
5. **Always communicate what you're working on**
6. **Never skip quality checks**

## Initial Beads (If BV empty)

If beads don't exist yet, create them for:

- **bd-001**: Initialize Tauri + React + TypeScript project
- **bd-002**: Set up Three.js + React Three Fiber
- **bd-003**: Set up shadcn/ui components
- **bd-004**: Initialize Python FastAPI server
- **bd-005**: Set up LangGraph agent graph
- **bd-006**: Create basic agent sprites (pixel art)
- **bd-007**: Implement first agent render on screen
- **bd-008**: Implement click detection for agents
- **bd-009**: Build agent detail panel
- **bd-010**: Connect frontend to Python backend

---

**Remember:** Every agent is fungible. Just start working and coordinate via Agent Mail!

*Last updated: 2026-02-02*

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds