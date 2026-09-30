# Copilot Instructions for DiscordLLMBot

## 1. Architecture Overview

This is a monorepo containing:
- **bot/** - Discord bot with Express API (TypeScript)
- **dashboard/** - React dashboard with TypeScript, Vite, MUI
- **shared/** - Common utilities (database, config, logging)
- **docs/** - Documentation site

This is a Discord bot that generates contextual replies using LLM APIs (Google Gemini, Ollama, or Qwen). The bot maintains a human personality and can customize behavior per user and per server. The entire environment is containerized using Docker Compose.

**Data Flow:**
1. User message → stored in PostgreSQL database
2. Prompt builder combines: bot persona + user relationship + conversation context + knowledge graph memory
3. LLM API (Gemini/Ollama/Qwen) generates reply → Bot responds in Discord

**Container Architecture:**
- **Single Bot Container:** The bot and API run in the same container (`bot` service)
- **Port 3000:** The Express + Socket.io API server runs on port 3000 within the bot container
- **Shared State:** The API has direct access to the Discord client and all bot state

---

## 2. Source-of-truth Configuration Model

Use the current normalized schema:

### Global config (`global_config`)
- `botPersona`: `username`, `description`, `globalRules[]`
- `llm`: `provider`, `geminiModel`, `ollamaModel`, `qwenModel`, `retryAttempts`, `retryBackoffMs`
- `memory`: `maxMessages`, `maxMessageAgeDays`
- `logger`: `maxLogLines`, `logReplyDecisions`, `logSql`
- `sandbox`: `enabled`, `timeoutMs`, `allowedCommands[]`

### Server config (`server_configs`)
- `nickname`
- `speakingStyle[]`
- `replyBehavior`:
  - `replyProbability`
  - `minDelayMs`
  - `maxDelayMs`
  - `mentionOnly`
  - `ignoreUsers[]`
  - `ignoreChannels[]`
  - `ignoreKeywords[]`
  - `guildSpecificChannels`

### Per-user relationships (`relationships`)
- `username`, `displayName`, `avatarUrl`
- `attitude` - string describing the user's attitude (e.g., "friendly", "hostile", "neutral")
- `behavior` - string describing how the bot should behave toward the user (e.g., "treat them like a close friend")
- `boundaries[]` - array of boundary strings
- `ignored` - boolean flag to ignore this user

### Persistence Policy

Configuration is persisted using typed columns (not a single JSON blob column). Keep persistence SQL aligned with schema setup in `shared/storage/database.js`.

No legacy/backward-compat adapters are required; rebuilding/resetting DB during development is acceptable.

---

## 3. Reply Logic Policy

Primary reply decision logic in `bot/src/core/replyDecider.ts` should remain:

1. ignore lists (user/channel/keyword),
2. relationship ignored flag,
3. `mentionOnly` gate,
4. probability gate.

Do not reintroduce legacy mode-based strategy flow unless explicitly requested.

---

## 4. Build, Lint, and Type-Check Commands

### Root (Monorepo with Turbo)
```bash
npm run dev           # Start bot, db, dashboard with Docker
npm run dev:build     # Rebuild and start
npm run dev:down      # Stop containers
npm run dev:all       # Start all services including docs
npm run dev:logs      # Follow all logs
npm run build         # Build all workspaces (Turbo cached)
npm run lint          # Lint all workspaces (parallel)
npm run type-check    # Type-check all workspaces
npm run test          # Run tests across workspaces
npm run docs          # Run docs dev server
npm run graph         # Generate dependency graph
npm run graph:circular # Check for circular dependencies
```

### Turbo-Specific Commands
```bash
npm run build:bot          # Build only bot workspace
npm run build:dashboard    # Build only dashboard
npm run build:shared       # Build only shared utilities
npm run turbo:clean        # Clean Turbo cache
npm run graph:svg          # Generate interactive SVG dependency graph
```

### Bot (TypeScript)
```bash
cd bot
npm run lint          # ESLint
npm run type-check    # TypeScript: tsc --noEmit
npm run dev           # Start with nodemon
npm run start         # node dist/index.js
```

### Dashboard (React + TypeScript)
```bash
cd dashboard
npm run dev           # Start Vite dev server (port 5173)
npm run lint          # ESLint
npm run type-check    # TypeScript: tsc --noEmit
npm run build         # Production build
npm run preview       # Preview production build
```

---

## 4.1. Turbo Monorepo Integration

This project uses [Turborepo](https://turbo.build/) for optimized monorepo builds:

- **Parallel execution** - Lint/type-check run across all workspaces simultaneously
- **Remote caching** - Build cache shared via `turbo-cache` Docker volume
- **Smart rebuilds** - Only affected packages are rebuilt
- **Task pipelines** - Dependencies built in correct order (shared → bot → dashboard)

**Configuration:**
- `turbo.json` - Task definitions and cache settings
- `.turboignore` - Files excluded from cache consideration
- `docker-compose.yml` - Turbo cache volume mounted to all services

See [TURBO.md](TURBO.md) for detailed documentation.

---

## 5. Code Style Guidelines

### Bot (TypeScript/ES Modules)

**Formatting & Linting**
- 4-space indentation (not tabs)
- Single quotes for strings
- Semicolons always
- Use ESLint rules from `bot/eslint.config.js`

**Key ESLint Rules**
- `prefer-const` - Use const by default, let only when reassigning
- `no-unused-vars` - Allow variables starting with `_` or `client`
- `no-console` - Off (use the logger utility instead)

**Imports**
- Use `.js` extensions for local imports
- Absolute paths from workspace root: `../../shared/utils/logger.js`

```javascript
// Good
import { logger } from '../../shared/utils/logger.js';
import { loadConfig } from '../../shared/config/configLoader.js';

// Bad
import("./foo.js");
```

**Null Handling**
- Use **nullish coalescing (`??`)** for defaults, NOT `||`
```javascript
// Good
const mode = replyBehavior.mode ?? 'mention-only';
const prob = typeof replyBehavior.replyProbability === 'number' 
    ? replyBehavior.replyProbability 
    : 1.0;

// Bad
const mode = replyBehavior.mode || 'mention-only';
```

**Error Handling**
- Wrap async operations in try/catch
- Log errors with the logger utility
- Let errors propagate when appropriate

```javascript
try {
    await someAsyncOperation();
} catch (err) {
    logger.error('Operation failed', err);
    throw err;
}
```

**Logging**
- Use the logger from `shared/utils/logger.js`
- Log levels: `logger.error`, `logger.warn`, `logger.info`, `logger.api`, `logger.message`, `logger.sql`

---

### Dashboard (TypeScript + React)

**TypeScript Configuration**
- Strict mode enabled via `typescript-eslint`
- Use types from `@/types` when available
- Avoid `any`

**Components**
- Use MUI components (`<REDACTED_USER>/material`)
- Follow existing component patterns in `src/pages/` and `src/components/`
- Use path aliases: `<REDACTED_USER>`, `<REDACTED_USER>`, `<REDACTED_USER>`, `<REDACTED_USER>`, `<REDACTED_USER>`, `<REDACTED_USER>`

```typescript
import theme from '<REDACTED_USER>';
import { Dashboard, Settings } from '<REDACTED_USER>';
import { useHealth } from '<REDACTED_USER>';
```

**React Patterns**
- Functional components with hooks
- Use `ErrorBoundary` for error handling
- Custom hooks in `src/hooks/`
- Debounced auto-save for settings (1-second delay)

**Styling**
- MUI `sx` prop for inline styles
- Dark theme from `src/theme.ts`

---

## 6. File Organization

```
bot/src/
  index.ts                           # Main entry point (Discord client + event registration)
  api/
    server.ts                        # Express + Socket.io API for dashboard (port 3000)
    routes/                          # Modular route handlers
    socket.ts                        # Socket.io event handlers
  llm/
    index.ts                         # Unified LLM provider interface
    gemini.ts                        # Google Gemini API with retry logic
    ollama.ts                        # Ollama local models with retry logic
    qwen.ts                          # Qwen API with OAuth support
  memory/
    context.ts                       # Channel-specific history + persistence
    knowledgeGraph.ts                # Long-term semantic memory with node/edge relationships
  personality/
    botPersona.ts                    # Bot identity configuration
    relationships.ts                 # Per-user relationship management
  core/
    prompt.ts                        # Builds prompts for LLM
    replyDecider.ts                  # Reply decision logic
    responseDelay.ts                 # Human-like delay calculation
  sandbox/
    dockerExecutor.ts                # Docker container executor for sandbox commands
    commandExtractor.ts              # LLM-based command extraction
    index.ts                         # Sandbox module exports
  events/
    messageCreate.ts                 # Message handling and reply logic
    guildCreate.ts                   # Guild join event handler
    index.ts                         # Event loader
  utils/
    profileUpdater.ts                # Sync Discord profile with config

shared/
  storage/
    database.ts                      # PostgreSQL connection + schema setup
    persistence.ts                   # Data access layer (CRUD operations)
  config/
    configLoader.ts                  # Config loading (global + per-server from DB)
  utils/
    logger.ts                        # Structured logging (file + console)

dashboard/src/
  pages/                             # Route pages (Dashboard, Settings, Servers, Logs, Playground)
  components/                        # Reusable UI components
  hooks/                             # Custom React hooks
  services/                          # API calls to bot
  theme.ts                           # MUI dark theme
```

---

## 7. Module Responsibilities

- **`bot/src/index.ts`**: Discord client setup, event registration, graceful shutdown
- **`bot/src/api/server.ts`**: Express + Socket.io API serving the dashboard
- **`bot/src/api/routes/`**: Modular API route handlers
- **`bot/src/api/socket.ts`**: Socket.io event handlers for real-time logging
- **`bot/src/llm/index.ts`**: Unified interface for Gemini, Ollama, and Qwen providers
- **`bot/src/memory/context.ts`**: Per-channel message history (in-memory cache + PostgreSQL persistence)
- **`bot/src/memory/knowledgeGraph.ts`**: Long-term semantic memory with node/edge relationships
- **`bot/src/personality/relationships.ts`**: Per-user relationship management
- **`bot/src/core/replyDecider.ts`**: Reply decision logic with configurable checks
- **`bot/src/sandbox/dockerExecutor.ts`**: Executes commands in isolated Docker containers
- **`bot/src/sandbox/commandExtractor.ts`**: Uses LLM to extract shell commands from user requests
- **`shared/storage/persistence.ts`**: All database CRUD operations
- **`shared/config/configLoader.ts`**: Loads global and per-server configuration from PostgreSQL
- **`shared/utils/logger.ts`**: Multi-level logging to file and console

---

## 8. Key Implementation Patterns

- **Nullish Coalescing:** Always use `??` for default values, not `||`
- **Persistence Layer:** All DB ops through `shared/storage/persistence.ts`
- **Exponential Backoff:** Retry logic with jitter in LLM calls
- **In-memory Cache:** `guildRelationships` and `guildContexts` with DB persistence
- **Debounced Auto-save:** Dashboard settings save after 1-second delay to prevent API spam
- **Docker Sandbox:** Commands run in isolated containers via Docker-in-Docker (DinD) for security
- **Knowledge Graph:** Long-term memory stored in `knowledge_graph` table with semantic retrieval

---

## 9. Dashboard Features

| Page | Features |
|------|----------|
| **Dashboard** | Stats (replies, active servers/users), activity volume, system health |
| **Settings** | Global config with tabs (Bot Persona, LLM, Memory, Logger, Sandbox), auto-save debouncing |
| **Servers** | Server list with per-server config, user relationships, channel monitoring |
| **Logs** | Real-time Socket.io streaming, filter by level, auto-scroll toggle |
| **Playground** | Chat interface to test bot responses |

---

## 10. Environment Variables

```bash
# Discord
DISCORD_TOKEN=
DISCORD_CLIENT_ID=

# LLM Provider
GEMINI_API_KEY=
OLLAMA_API_URL=
QWEN_API_KEY=

# Optional Qwen OAuth (PKCE device flow)
QWEN_OAUTH_CLIENT_ID=

# PostgreSQL
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_PORT=
DATABASE_URL=

# pgAdmin
PGADMIN_DEFAULT_EMAIL=
PGADMIN_DEFAULT_PASSWORD=

# Ports
API_PORT=3000
DASHBOARD_PORT=5173
DOCS_PORT=5174

# Ollama (Docker)
OLLAMA_API_URL=http://host.docker.internal:11434

# Qwen OpenAI-compatible endpoint
QWEN_API_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
```

---

## 11. Database Schema

Key tables:
- `global_config` — System-wide settings (typed columns)
- `server_configs` — Per-server overrides (typed columns)
- `guilds` — Joined servers
- `relationships` — Per-user relationship data
- `relationship_behaviors` — Behavior definitions for relationships
- `relationship_boundaries` — Boundary definitions for relationships
- `messages` — Message history
- `bot_replies` — Reply analytics
- `knowledge_graph` — Long-term memory nodes and edges

---

## 12. Common Tasks

### Adding a New Feature
1. Determine location (which module: `memory`, `llm`, `personality`, `core`, `api`)
2. Consider prompt impact
3. Use relationships for per-user data
4. Add logging via logger utility
5. Add API endpoints in `bot/src/api/server.ts` if dashboard integration needed
6. Update dashboard component if UI exposure needed

### Debugging
1. Check `discordllmbot.log` for errors and API traces
2. Review `bot/src/events/messageCreate.ts` for message flow
3. Check `bot/src/core/replyDecider.ts` for reply decision logic
4. Use dashboard Logs page for real-time logs
5. Verify configuration in database (use pgAdmin at http://localhost:5050)
6. Check knowledge graph memory in `bot/src/memory/knowledgeGraph.ts`

---

## 13. Recent Updates

- **Knowledge Graph Memory**: Integrated long-term semantic memory system with node/edge relationships
- **Qwen OAuth**: Automatic token refresh on 401 errors for Qwen API
- **Modular API**: Refactored `server.ts` into modular route files in `bot/src/api/routes/`
- **Docker Networking**: Fixed service discovery and proxy configuration for container communication
- **Type Safety**: Added path aliases and centralized constants for bot, dashboard, and shared
- **Socket.io**: Implemented single shared socket pattern, fixed memory leaks in dashboard