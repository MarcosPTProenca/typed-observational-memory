# Koios - Autonomous Canvas LMS Agent

Named after the Greek Titan of intellect. A self-hosted replica of [companion.ai/einstein](https://companion.ai/einstein).

## What This Is

An autonomous AI agent built on **OpenClaw** that handles Canvas LMS coursework. The agent is fully autonomous — give it Canvas access (cookies, API token, or credentials) and it figures out the rest: authenticating, discovering courses, tracking assignments, doing work, and submitting.

## Architecture

- **Runtime**: OpenClaw gateway (long-lived Node.js process at `ws://<REDACTED_IP>:18789`)
- **LLM**: AWS Bedrock (Claude Sonnet 4.6) via `bedrock-converse-stream` API
- **Browser**: OpenClaw-managed headless Chromium (Playwright) — the agent controls this itself
- **Auth**: Agent handles autonomously. Supports cookies, API tokens, or username/password login. It decides which method to use.

## How to Interact

Talk to Koios via:
- `openclaw agent --local --session-id main --message "your message"` (CLI)
- OpenClaw dashboard at `http://<REDACTED_IP>:18789/` (web)
- Any connected channel (Telegram, Discord, etc.) once configured

## OpenClaw Workspace

Lives at `~/.openclaw/workspace/`. All markdown files are loaded into the agent's system prompt each turn.

| File | Purpose |
|------|---------|
| `IDENTITY.md` | Agent name (Koios), role, vibe |
| `SOUL.md` | Personality, capabilities, operating principles |
| `AGENTS.md` | Workspace structure, workflows, how the agent should behave |
| `USER.md` | Human's info — blank template, filled by the agent as it learns |
| `TOOLS.md` | How to use Canvas, browser, auth — agent-facing instructions |
| `HEARTBEAT.md` | Periodic checks (deadlines, announcements, grades) |
| `MEMORY.md` | Curated long-term memory |
| `memory/YYYY-MM-DD.md` | Daily append-only logs |

## Skills

Single skill: `school-agent` at `workspace/skills/school-agent/SKILL.md`

Handles: Canvas authentication (all methods), course discovery, assignment tracking, lecture processing, discussion participation, work completion, submission.

## Workspace Directories

```
~/.openclaw/workspace/
  auth/                    # Stored by the agent after authentication
    config.json            # Canvas URL, auth method, API token
    canvas-cookies.json    # Cookie backup
  classes/                 # Course tracking (created by agent)
    <course-code>/
      README.md            # Syllabus, schedule, grading
      assignments/<name>/
        README.md          # Requirements, status
        work/              # Completed work
      notes/               # Lecture notes
  daily-briefs/            # Daily status reports
```

## OpenClaw Config

`~/.openclaw/openclaw.json`:
```json
{
  "models": {
    "providers": {
      "amazon-bedrock": {
        "baseUrl": "https://bedrock-runtime.<YOUR_REGION>.amazonaws.com",
        "api": "bedrock-converse-stream",
        "auth": "aws-sdk",
        "models": [{
          "id": "us.anthropic.claude-sonnet-4-6",
          "name": "Claude Sonnet 4.6 (Bedrock)",
          "contextWindow": 200000,
          "maxTokens": 8192
        }]
      }
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "amazon-bedrock/us.anthropic.claude-sonnet-4-6"
      }
    }
  }
}
```

AWS credentials: uses the standard AWS SDK credential chain (`~/.aws/credentials` or env vars).

## Setup

Run `./setup.sh` — it installs OpenClaw, copies workspace files, configures Bedrock, and starts the gateway. Requires Node.js 22+ and AWS CLI with Bedrock access.

## Versioning & Commits

This project uses [Semantic Versioning](https://semver.org/) and [Conventional Commits](https://www.conventionalcommits.org/).

### Semantic Versioning (MAJOR.MINOR.PATCH)

- **PATCH** (0.0.X) — Bug fixes, typo corrections, minor tweaks that don't change behavior
- **MINOR** (0.X.0) — New features, new skills, new Canvas endpoints — backwards compatible
- **MAJOR** (X.0.0) — Breaking changes to workspace file format, config schema, or setup flow

While in initial development (`0.x.x`), the API is not considered stable.

### Conventional Commits

All commit messages follow the format: `<type>: <description>`

| Type | When to use | Version bump |
|------|------------|--------------|
| `feat` | New feature or capability | MINOR |
| `fix` | Bug fix | PATCH |
| `docs` | Documentation only | — |
| `refactor` | Code restructure, no behavior change | — |
| `chore` | Maintenance, config, tooling | — |
| `perf` | Performance improvement | PATCH |

Breaking changes append `!` after the type: `feat!: restructure workspace file format`

Examples:
```
feat: add canvas-auth skill with cookie support
fix: handle expired session redirect in browser auth
docs: add setup instructions to CLAUDE.md
refactor: consolidate auth scenarios in school-agent skill
chore: update .gitignore to exclude daily-briefs
```

## Origin

Inspired by [companion.ai/einstein](https://companion.ai/einstein) which runs on OpenClaw.

## Canvas API Reference

All under `<canvas-url>/api/v1/`:
```
GET  <REDACTED_USERPATH>                                        # Verify auth
GET  /courses?enrollment_state=active                   # List courses
GET  /courses/:id/assignments                           # Assignments + due dates
GET  /courses/:id/discussion_topics                     # Discussions
GET  /courses/:id/discussion_topics/:id/entries         # Thread entries
POST /courses/:id/discussion_topics/:id/entries         # Post reply
GET  /courses/:id/modules                               # Modules
GET  /courses/:id/modules/:id/items                     # Module items
GET  /courses/:id/pages/:url                            # Page content
POST /courses/:id/assignments/:id/submissions           # Submit work
```