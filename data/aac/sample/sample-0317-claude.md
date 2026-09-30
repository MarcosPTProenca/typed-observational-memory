# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MoYuCode（摸鱼Coding） is a dual-stack application providing a web UI for AI coding assistants (Codex and Claude Code). The backend is an ASP.NET Core Web API (net10.0) that integrates with the OpenAI Codex app-server via JSON-RPC over stdio. The frontend is a Vite + React + TypeScript SPA with Tailwind CSS.

## Build Commands

### Backend (C# API)
- Build: `dotnet build src/MoYuCode/MoYuCode.csproj`
- Run (HTTP): `dotnet run --project src/MoYuCode/MoYuCode.csproj --launch-profile http`
  - Runs on `http://localhost:9110`
- Run (HTTPS): `dotnet run --project src/MoYuCode/MoYuCode.csproj --launch-profile https`
  - Runs on `https://localhost:9111`

### Windows Desktop App (MoYuCode.Win)
- Build: `dotnet build src/MoYuCode.Win/MoYuCode.Win.csproj`
- Run: `dotnet run --project src/MoYuCode.Win/MoYuCode.Win.csproj`
- This is a Windows Forms app that hosts the API with a system tray icon

### Frontend (React)
All commands should be run from the `web/` directory:
- Install dependencies: `npm ci`
- Dev server: `npm run dev`
- Build: `npm run build` (runs TypeScript check + Vite build)
- Lint: `npm run lint`

### Full Application Build
To build the complete application with frontend bundled:
```bash
cd web && npm ci && npm run build && cd ..
# Copy frontend build to backend wwwroot (use xcopy on Windows, rsync on Unix)
dotnet build src/MoYuCode/MoYuCode.csproj -c Release
```

## Architecture

### Backend Structure

The API follows a hybrid architecture with both minimal APIs and traditional controllers:

**Minimal APIs** (`Api/` directory):
- `ApiEndpoints.cs`: Main REST API endpoints (filesystem, projects, providers, tools, jobs)
- `A2aEndpoints.cs`: Agent-to-Agent (A2A) protocol endpoints for streaming AI interactions
  - Implements `.well-known/agent.json` discovery
  - JSON-RPC over Server-Sent Events (SSE) for real-time streaming
  - Methods: `tasks/sendSubscribe`, `tasks/resubscribe`, `tasks/get`, `tasks/cancel`

**Controllers** (`Controllers/` directory):
- Traditional ASP.NET controllers for REST operations
- `FileSystemController`, `ProjectsController`, `ProvidersController`, `ToolsController`, `JobsController`

**Services** (`Services/` directory):
- `Codex/CodexAppServerClient`: Manages Codex CLI process lifecycle and JSON-RPC communication
  - Launches `codex app-server` as a child process
  - Handles stdin/stdout/stderr streams
  - Windows-specific logic to resolve npm-installed Codex binary paths
  - Publishes events to subscribers via Channels
- `Codex/CodexSessionManager`: Manages Codex thread lifecycle per session
- `A2a/A2aTaskManager`: Orchestrates A2A tasks, pumps Codex events, builds SSE streams
  - Collects assistant text, reasoning, tool output, diffs, token usage
  - Maintains event history for replay/resubscription
- `Jobs/JobManager`: Background job management
- `Shell/PowerShellLauncher`: PowerShell execution

**Data** (`Data/` directory):
- `MyYuCodeDbContext`: Entity Framework Core context (SQLite)
- Entities: `ProjectEntity`, `ProviderEntity`
- Database location: `%LOCALAPPDATA%\myyucode\myyucode.sqlite`
- Migrations: `LogMigrations/` directory

### Frontend Structure

**Routing** (`App.tsx`):
- `/codex`: Codex tool page
- `/claude`: Claude Code tool page
- `/providers`: Provider management page
- `/projects/:id`: Project workspace with session visualization

**Key Components**:
- `CodexSessionViz.tsx`: Visualizes Codex session events (reasoning, diffs, tool output, token usage)
- `ProjectWorkspacePage.tsx`: Main workspace for interacting with projects
- `DirectoryPicker.tsx`: File system navigation
- `animate-ui/`: Custom animated UI component library built on Radix UI

**State Management**:
- React Router for navigation
- Local component state (useState, useReducer)
- No global state management library (Redux/Zustand not used for app state, though Zustand is a dependency)

**Styling**:
- Tailwind CSS v4 with `<REDACTED_USER>/vite` plugin
- Theme system with dark mode support (`next-themes`)
- Path alias: `@/` maps to `web/src/`

### MoYuCode.Win (Windows Desktop)

`src/MoYuCode.Win/` is a Windows Forms application that:
- Hosts the MoYuCode（摸鱼Coding） API as an embedded web server
- Displays a system tray icon for background operation
- References the main `MoYuCode` project and runs it in-process

### Codex Integration Flow

1. **Process Lifecycle**: `CodexAppServerClient` starts `codex app-server` on first use
2. **Initialization**: Sends `initialize` JSON-RPC call with client info
3. **Thread Management**: `CodexSessionManager` creates/reuses threads per session
4. **Turn Execution**: A2A tasks trigger `turn/start` with user input
5. **Event Streaming**: Codex notifications are pumped through channels
   - `item/agentMessage/delta`: Assistant text chunks
   - `item/reasoning/textDelta`: Reasoning text chunks
   - `item/commandExecution/outputDelta`: Tool output chunks
   - `turn/diff/updated`: File diff updates
   - `thread/tokenUsage/updated`: Token usage updates
   - `turn/completed`: Final status (completed/failed/interrupted)
6. **A2A Streaming**: Events are converted to A2A protocol and streamed via SSE to clients

### Configuration

- `appsettings.json` / environment variables
- `Codex:ExecutablePath`: Optional override for Codex CLI path (falls back to PATH resolution)
- CORS: Configured to allow any origin (development setup)

## Coding Conventions

### C# (Backend)
- 4-space indentation
- Nullable reference types enabled (avoid new warnings)
- `PascalCase` for types, methods, properties
- `camelCase` for locals, parameters
- Use `required` properties for DTOs/records
- Prefer records for DTOs and immutable data structures
- Endpoint filters: `ApiResponseEndpointFilter` wraps responses in `ApiResponse<T>`

### TypeScript (Frontend)
- Components: `PascalCase.tsx`
- Hooks: `useX.ts` or `useX.tsx`
- Use `@/` path alias for imports
- Prefer `const` arrow functions for components
- Use Tailwind CSS utility classes (avoid inline styles)

## Database Migrations

Entity Framework Core migrations are in `src/MoYuCode/LogMigrations/`.

To create a migration:
```bash
dotnet ef migrations add MigrationName --project src/MoYuCode/MoYuCode.csproj --context MyYuCodeDbContext --output-dir LogMigrations
```

To update the database (runs automatically on app startup):
```bash
dotnet ef database update --project src/MoYuCode/MoYuCode.csproj --context MyYuCodeDbContext
```

## Windows-Specific Notes

- Codex resolution: Prefers vendored binaries in `%APPDATA%\npm\node_modules\<REDACTED_USER>\codex\vendor\{arch}\codex\codex.exe`
- Fallback: Invokes `.cmd` shim via `cmd.exe /c` (required for `UseShellExecute=false`)
- Architecture detection: ARM64 → `aarch64-pc-windows-msvc`, x64 → `x86_64-pc-windows-msvc`
- Line endings: Codex stdin requires LF (`\n`), not CRLF (explicitly set in `StreamWriter.NewLine`)

## Testing

No automated tests are currently configured. When adding tests:
- Place under `tests/` directory
- Use xUnit for C# tests
- Ensure `dotnet test` runs all tests

## Commit Conventions

Use Conventional Commits format:
- `feat: …` for new features
- `fix: …` for bug fixes
- `chore: …` for maintenance tasks
- `docs: …` for documentation changes

## Common Development Tasks

1. **Reset local database**: Delete `%LOCALAPPDATA%\myyucode\myyucode.sqlite` and restart the API
2. **Debug Codex integration**: Check backend logs for `codex[stderr]` warnings and JSON-RPC traffic
3. **Install Codex CLI**: `npm install -g <REDACTED_USER>/codex` (required for backend functionality)