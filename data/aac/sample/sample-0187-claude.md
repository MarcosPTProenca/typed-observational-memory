# zabicekiosk - AI Assistant Instructions

## Project Overview

You are working on **zabicekiosk**, a kiosk and admin application for online accounting and booking of infant swimming exercises.

**Domain**: Infant swimming class management (booking, passes, client management)
**Tech Stack**: TypeScript, Fastify, React, Firebase/Firestore, Google Cloud Platform

---

## For AI Agents: Start Here

### Agent Manifest System

**Each specialized agent has a dedicated manifest with priority-ordered documentation.**

**Your manifest location**: `docs/agents/{your-agent-name}.md`

**Quick Start**:
1. MUST read your manifest: `docs/agents/{your-agent-name}.md`
2. Load Priority 1 docs from your manifest (core domain knowledge)
3. Reference Priority 2 docs frequently during implementation
4. Follow quality gates in your manifest

**Available Agent Manifests**:
- `docs/agents/lean-architect.md` - System architecture and technical specifications
- `docs/agents/typescript-engineer.md` - TypeScript backend services (core-api, booking-api)
- `docs/agents/react-engineer.md` - React frontend applications (admin-portal, kiosk-pwa, parent-web)
- `docs/agents/database-engineer.md` - Firestore collections, security rules, data modeling
- `docs/agents/devops.md` - Firebase deployment, GitHub Actions, GCP infrastructure
- `docs/agents/test-engineer.md` - Testing strategy, Jest, Playwright, coverage
- `docs/agents/quality-reviewer.md` - Quality assurance, binary acceptance decisions
- `docs/agents/task-engineer.md` - Task creation, backlog management
- `docs/agents/retro.md` - Process improvement, root cause analysis
- `docs/agents/precommit.md` - Pre-commit hooks, quality gate enforcement

**Manifest System Overview**: `docs/agents/README.md`

---

## 🚨 MANDATORY: Pure Delegation Architecture

**CRITICAL ENFORCEMENT**: The main Claude Code assistant is a PURE ORCHESTRATOR. You MUST delegate ALL work to specialist agents.

### Absolute Prohibitions

**NEVER execute directly**:
- Implementation (code, TypeScript, React components)
- Documentation writing (specs, guides, READMEs)
- Design work (architecture, UI/UX, data models)
- Testing (unit tests, integration tests, E2E tests)
- Infrastructure setup (deployment, CI/CD, Firebase config)
- Quality review (code review, acceptance testing)
- Task creation (backlog management)
- Process improvements (retrospectives, workflow updates)

### Mandatory Delegation Protocol

**ALWAYS follow this sequence**:

1. **Analyze Request**: Understand user's requirements completely
2. **Break Down Scope**: Decompose into specialist-agent-sized chunks
3. **Identify Specialists**: Map chunks to available agents
4. **Delegate**: Use Task tool to launch appropriate specialist agent(s)
5. **Coordinate**: Manage dependencies and sequencing between agents
6. **Report**: Summarize results to user after specialists complete

### Agent Selection Matrix

| User Request Type | Delegate To | Example |
|-------------------|-------------|---------|
| "Design the booking system architecture" | lean-architect | System architecture, component design |
| "Implement booking API endpoints" | typescript-engineer | Fastify service implementation |
| "Build admin portal booking page" | react-engineer | React component implementation |
| "Design Firestore schema for sessions" | database-engineer | Schema design, security rules |
| "Deploy services to Cloud Run" | devops | GCP deployment, CI/CD |
| "Write E2E tests for booking flow" | test-engineer | Playwright tests |
| "Review completed feature" | quality-reviewer | Quality validation, acceptance |
| "Create task for session management" | task-engineer | Task specification, backlog entry |
| "Analyze why tasks keep failing" | retro | Root cause analysis, process improvement |
| "Set up TypeScript pre-commit hooks" | precommit | Quality gate configuration |

---

## Core Specifications

**Project Structure**:

```
zabicekiosk/
├── services/              # Backend services
│   ├── core-api/         # Fastify - Core operations API
│   └── booking-api/      # Fastify - Booking and scheduling API
│
├── web/                   # Frontend applications
│   ├── admin-portal/     # React - Admin backoffice
│   ├── kiosk-pwa/        # React PWA - Kiosk for scanning passes
│   └── parent-web/       # React - Parent portal
│
├── infra/                 # Terraform - GCP infrastructure
├── .github/workflows/     # GitHub Actions - CI/CD
├── docs/                  # Documentation
│   ├── acf/              # ACF process documentation
│   └── agents/           # Agent manifests
├── .backlog/             # Task management
└── Makefile              # Development commands
```

---

## Tech Stack Constraints

### Required Technologies

**Backend Services**:
- **TypeScript** with strict mode
- **Fastify** framework
- **Firebase Admin SDK** for Firestore
- **Node.js** 18+

**Frontend Applications**:
- **React** with TypeScript
- **Vite** build tool
- **CSS Modules** for styling
- **React Router** for routing

**Data Infrastructure**:
- **Firestore** for all data storage
- **Firebase Security Rules** for authorization
- **Firebase Hosting** for static apps

**Infrastructure**:
- **Google Cloud Platform** (Cloud Run, Cloud Build)
- **Firebase** (Hosting, Firestore, Auth)
- **Terraform** for infrastructure as code
- **GitHub Actions** for CI/CD

**Testing**:
- **Jest** for unit tests
- **Testing Library** for React component tests
- **Playwright** for E2E tests

---

## Architecture Guidelines

### Monorepo Structure

- **services/** - Backend APIs (TypeScript + Fastify)
- **web/** - Frontend apps (React + TypeScript)
- **infra/** - Infrastructure as code (Terraform)

### Service Communication

**Backend to Frontend**:
- REST APIs (JSON responses)
- OpenAPI specifications in openapi.yaml

**Backend to Firestore**:
- Firebase Admin SDK
- Server-side authentication

**Frontend to Backend**:
- Fetch API
- Client in src/lib/api.ts

---

## Quality Standards

### TypeScript Services (core-api, booking-api)

```bash
cd services/core-api
npm run lint          # ESLint
npm run typecheck     # TypeScript compiler
npm run build         # Build check
npm test              # Jest with >80% coverage
```

### React Apps (admin-portal, kiosk-pwa, parent-web)

```bash
cd web/admin-portal
npm run lint          # ESLint
npm run typecheck     # TypeScript compiler
npm run build         # Vite build
npm test              # Jest with >70% coverage
```

### All Projects

```bash
make quality          # Run all quality checks
```

---

## DO NOT

1. **DO NOT** implement custom auth - use Firebase Auth
2. **DO NOT** bypass TypeScript strict mode
3. **DO NOT** use `any` types without explicit justification
4. **DO NOT** skip tests - all new code needs tests
5. **DO NOT** commit without running quality gates
6. **DO NOT** hardcode secrets - use environment variables
7. **DO NOT** deploy to production without review
8. **DO NOT** create tasks without binary acceptance criteria

---

## ACF Configuration

### Documentation Organization

```
docs/
├── agents/              # Agent manifests (START HERE)
└── acf/                 # ACF process documentation
    ├── backlog/         # Task workflow
    ├── git/             # Git conventions
    └── style/           # Communication styles
```

### Task Workflow

**States**: draft → pending → in-progress → completed → in-review → [accepted|rejected]

**Locations**:
```
.backlog/
├── draft/           # User-controlled (excluded from automation)
├── pending/         # Ready to start
├── in-progress/     # Active work
├── completed/       # Awaiting review
├── in-review/       # Under quality review
├── rejected/        # Needs fixes (max 3 retries)
├── blocked/         # Unresolvable or max retries exceeded
└── accepted/        # Done (SUCCESS)
```

**See**: `docs/acf/backlog/workflow.md`

### Quality Gates

**See**: `docs/acf/style/general.md` (single source of truth)

**Summary**:

**TypeScript Services**:
```bash
npm run lint && npm run typecheck && npm run build && npm test
```

**React Apps**:
```bash
npm run lint && npm run typecheck && npm run build && npm test
```

**Zero bypass tolerance**: NEVER use `--no-verify`, `// eslint-disable` without justification

### Git Commit Conventions

**Key Rules:**
- FORBIDDEN: `git add .`, `git add -A`, `git commit -a` (bulk staging)
- REQUIRED: Stage files explicitly by full path
- FORMAT: Conventional Commits (feat/fix/docs/etc.)
- ATOMIC: Commit after each completed task

**Full specification**: `docs/acf/git/commit-conventions.md`

---

## Development Commands

```bash
make help             # Show all commands
make install          # Install all dependencies
make dev              # Start development servers
make build            # Build all projects
make test             # Run all tests
make quality          # Run all quality checks
make clean            # Clean build artifacts

make firebase-emulators  # Start Firebase emulators
make deploy-dev       # Deploy to dev environment
make deploy-prod      # Deploy to production

make acf-backlog      # Show backlog status
make acf-agents       # List available agents
```

---

## Quick Start for Development

```bash
# Install dependencies
make install

# Start Firebase emulators
make firebase-emulators

# In another terminal, start dev servers
make dev

# Make changes, run quality checks
make quality

# Deploy to dev
make deploy-dev
```

---

## Communication Styles

Different contexts require different styles (see `docs/acf/style/README.md`):

- **General**: `docs/acf/style/general.md` - All agents, normal communication
- **Task Descriptions**: `docs/acf/style/task-descriptions.md` - task-engineer only, binary outcomes

---

## Remember

- **START WITH YOUR AGENT MANIFEST** (`docs/agents/{your-name}.md`)
- This is a monorepo - services and web apps coexist
- Use Firebase/Firestore for all data operations
- TypeScript strict mode everywhere
- Test coverage requirements: >80% services, >70% web apps
- Quality gates must pass before commits
- **DELEGATE ALL WORK** - Main assistant only orchestrates

---

**Last Updated**: 2025-11-03
**ACF Framework Version**: 1.0 (adapted for zabicekiosk)