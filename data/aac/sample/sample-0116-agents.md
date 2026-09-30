# Repository Guidelines

## Project Structure and Module Organization
- `src/app/` holds Next.js App Router routes, layouts, and page-level components.
- `src/components/` contains reusable UI components.
- `src/lib/` provides shared helpers (auth, utilities, etc.).
- `src/database/` contains database connection and models.
- `src/i18n/` and `messages/` store localization config and locale JSON files.
- `src/types/` includes shared TypeScript types.
- `public/` is for static assets.
- `src/middleware.ts` defines request middleware.
- Root configs live in `next.config.ts`, `tailwind.config.ts`, and `tsconfig.json`.

## Build, Test, and Development Commands
- `npm run dev` starts the local dev server (Turbopack) at `http://localhost:3000`.
- `npm run build` creates a production build.
- `npm run start` runs the production server from the build output.
- `npm run lint` runs Next.js ESLint checks.
- `npm run init` generates `.env` values via `init-template.js` prompts.
- `npm run prepare` installs Husky hooks if you use Git hooks locally.

## Coding Style and Naming Conventions
- Format with Prettier (2 spaces, semicolons, double quotes, print width 80).
- ESLint is enforced via `next lint`; run it before pushing.
- Prefer `PascalCase` for components (e.g., `ResumeCard.tsx`) and `camelCase` for functions.
- Keep route segment folders lowercase (e.g., `src/app/account-settings/`).

## Testing Guidelines
- No test framework is configured yet and there is no coverage requirement.
- If you add tests, follow `*.test.ts` or `*.test.tsx` naming and colocate near the module or under a `__tests__/` folder.

## Commit and Pull Request Guidelines
- Git history uses short, lowercase commit messages (e.g., "fix", "final fix") and no formal convention.
- Keep commits small and descriptive in the imperative mood.
- PRs should include: a concise summary, steps to verify, and screenshots for UI changes.
- Call out `.env` or config changes explicitly and link related issues if applicable.

## Localization and Configuration Tips
- Update translations in `messages/*.json` and keep keys consistent across locales.
- Use `.env.example` as the baseline for required environment variables.