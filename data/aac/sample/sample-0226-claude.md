# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Development Commands

```bash
# Monorepo commands (from root)
bun dev                        # Start both web (3000) and API (3002) servers
bun run build                  # Build all apps
bun lint                       # Lint all apps
bun start                      # Start production servers

# Filter to specific app
bun run dev -- --filter=web    # Only web app
bun run dev -- --filter=api    # Only API server
```

### Database Commands (Drizzle ORM)

```bash
bun run db:generate  # Generate migrations from schema changes
bun run db:migrate   # Run pending migrations
bun run db:push      # Push schema directly (dev only)
bun run db:studio    # Open Drizzle Studio GUI
```

## Architecture Overview

LogoLoco is an AI logo generation SaaS built as a Turborepo monorepo with Bun.

### Monorepo Structure

```
apps/
├── web/   # Next.js 15 frontend (port 3000)
└── api/   # Hono + Bun API server (port 3002)
```

### Web App (`apps/web`)
- Next.js 15 with App Router + Turbopack
- React 19 + TypeScript
- shadcn/ui components (Radix primitives + Tailwind v4)
- Path alias: `@/*` maps to `apps/web/`
- TanStack Query client is provided via `AppProvider`/`QueryProvider` (see `apps/web/app/layout.tsx` and `apps/web/components/providers/query-provider.tsx`). Use TanStack Query for client data fetching, polling, and auth flows.

### API Server (`apps/api`)
- Hono framework running on Bun
- Drizzle ORM with PostgreSQL
- Better Auth server in `src/auth.ts` (drizzle adapter, handler mounted at `/api/auth/*`)
- Anonymous auth plugin enabled
- Routes in `src/routes/`, database schemas in `src/db/schemas/` (migrations in `src/db/migrations/`)

### Data Flow

1. **Logo Generation**: Client submits form → `POST /api/predictions` creates DB record and calls Eachlabs API → Returns prediction ID → Client polls `GET /api/predictions/{id}` until complete
2. **Model Mapping**: Frontend model names map to Eachlabs API names:
   - `nano-banana` → `nano-banana`
   - `seedream-v4` → `seedream-v4-text-to-image`
   - `reve-text` → `reve-text-to-image`
3. **Credits**: 1 credit per logo output (max 4 per request). Credits are deducted upfront and refunded on provider failures. `GET /api/predictions/:id` is authenticated and locked to the owner of the generation.
4. **History**: `GET /api/predictions` is auth-only, paginated (limit/offset), filtered to the requesting user, and limited to retention window (`GENERATION_RETENTION_DAYS`, default 365). Frontend history hook consumes this endpoint with credentials.

### Environment Variables

**API (`apps/api/.env`):**
- `DATABASE_URL` - PostgreSQL connection string (required)
- `DATABASE_SSL` - Set to "true" for SSL connections
- `EACHLABS_API_KEY` - API key for logo generation
- `PORT` - API server port (default: 3002)
- `BETTER_AUTH_SECRET` - Required for Better Auth
- `BETTER_AUTH_URL` - Base URL for Better Auth server (API origin)
- `ALLOWED_ORIGINS` - Comma-separated CORS origins (credentials enabled)
- `PGPOOL_MAX`, `PGPOOL_IDLE_MS`, `PGPOOL_CONN_TIMEOUT_MS` - Pool tuning
- `SIGNUP_BONUS_CREDITS` - Initial credits granted on first auth (default 1)
- `ADMIN_EMAILS` - Comma-separated list of admin emails for `/api/admin/*`
- `GENERATION_RETENTION_DAYS` - Retention window for history listing (default 365)

**Web (`apps/web/.env.local`):**
- `NEXT_PUBLIC_API_BASE_URL` - API endpoint (required, points to API origin)

### Key Files

- `apps/api/src/routes/predictions.ts` - Core logo generation logic, history listing, and Eachlabs integration
- `apps/api/src/db/schemas/` - Database schemas (auth, credits, generations)
- `apps/api/src/db/migrations/0002_better_auth_fk.sql` - Better Auth tables + FK on `logo_generations.user_id` (ON DELETE SET NULL)
- `apps/web/components/logo-maker.tsx` - Main form component with TanStack Query mutations + polling logic
- `apps/web/hooks/use-history.ts` - History fetch (auth-required, uses `/api/predictions`)
- `apps/web/components/mvpblocks/login-form-3.tsx` & `register-form.tsx` - Better Auth client flows powered by TanStack Query