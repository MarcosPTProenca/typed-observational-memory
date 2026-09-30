# Repository Guidelines

## Project Structure & Module Organization
- `src/app/`: Next.js App Router pages, layouts, and route handlers (e.g., `src/app/posts/`, `src/app/projects/`).
- `src/components/`: shared UI and layout components (e.g., `site-header.tsx`, `post-card.tsx`).
- `src/lib/`: content and formatting helpers (e.g., `posts.ts`, `format.ts`).
- `content/`: Markdown source for blog posts.
- `public/`: static assets (images, `avatar.svg`, `favicon.svg`).
- `types/`: shared TypeScript type declarations.

## Build, Test, and Development Commands
- `pnpm dev`: start local dev server with hot reload.
- `pnpm build`: build the production bundle.
- `pnpm start`: run the production server after build.
- `pnpm lint`: run ESLint checks.

## Coding Style & Naming Conventions
- Language: TypeScript + React (Next.js). Use 2-space indentation and keep JSX tidy.
- Components: `PascalCase` filenames (e.g., `PostCard`, `SiteHeader`).
- Utilities: `camelCase` exports in `src/lib/`.
- Styling: Tailwind CSS utility classes; avoid custom CSS unless necessary.
- Linting: ESLint via `pnpm lint`. No formatter is configured; keep changes minimal and consistent.
 - Quotes: Prefer single quotes for JS/TS and JSX attributes.
 - Semicolons: Omit semicolons (enforced via ESLint `semi: never`).

## Testing Guidelines
- No automated test framework is currently configured.
- If adding tests, document the framework and add a `pnpm test` script.
- Name tests by feature and location (e.g., `posts.test.tsx`) when introduced.

## Commit & Pull Request Guidelines
- Commit messages follow conventional prefixes seen in history: `feat:`, `chore:`, `fix:`.
- Keep commits focused and scoped to a single concern.
- PRs should include:
  - a short description of the change,
  - screenshots for UI updates (especially pages/components),
  - linked issues if applicable.

## Configuration Notes
- Site metadata lives in `src/lib/site.ts`.
- Content rendering is handled by `src/lib/posts.ts` and consumes Markdown in `content/`.