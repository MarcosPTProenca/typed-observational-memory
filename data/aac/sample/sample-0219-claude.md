<!-- nx configuration start-->
<!-- Leave the start & end comments to automatically receive updates. -->

# General Guidelines for working with Nx

- For navigating/exploring the workspace, invoke the `nx-workspace` skill first - it has patterns for querying projects, targets, and dependencies
- When running tasks (for example build, lint, test, e2e, etc.), always prefer running the task through `nx` (i.e. `nx run`, `nx run-many`, `nx affected`) instead of using the underlying tooling directly
- Prefix nx commands with the workspace's package manager (e.g., `pnpm nx build`, `npm exec nx test`) - avoids using globally installed CLI
- You have access to the Nx MCP server and its tools, use them to help the user
- For Nx plugin best practices, check `node_modules/<REDACTED_USER>/<plugin>/PLUGIN.md`. Not all plugins have this file - proceed without it if unavailable.
- NEVER guess CLI flags - always check nx_docs or `--help` first when unsure

## Scaffolding & Generators

- For scaffolding tasks (creating apps, libs, project structure, setup), ALWAYS invoke the `nx-generate` skill FIRST before exploring or calling MCP tools

## When to use nx_docs

- USE for: advanced config options, unfamiliar flags, migration guides, plugin configuration, edge cases
- DON'T USE for: basic generator syntax (`nx g <REDACTED_USER>/react:app`), standard commands, things you already know
- The `nx-generate` skill handles generator discovery internally - don't call nx_docs just to look up generator syntax

<!-- nx configuration end-->

---

## Workspace Conventions

### Stack

- **Workspace**: Nx 22+ (preset npm, pnpm workspaces, TS project references)
- **Build**: Vite via `<REDACTED_USER>/vite/plugin`
- **Test**: Vitest via `<REDACTED_USER>/vitest`
- **Lint**: ESLint 9+ flat config via `<REDACTED_USER>/eslint/plugin`
- **Format**: Prettier 3 + `prettier-plugin-organize-imports`
- **TypeScript**: strict, `nodenext`, composite project references
- **Git hooks**: Lefthook (commit-msg, pre-commit, pre-push)
- **Commits**: Conventional commits via commitlint
- **Release**: Nx Release (independent versioning, conventional commits, GitHub releases)
- **Registry**: Verdaccio (local npm registry for testing publish)

### Commands

```bash
# Per-package
pnpm nx build <pkg>
pnpm nx test <pkg>
pnpm nx lint <pkg>
pnpm nx typecheck <pkg>

# Affected (CI/hooks)
pnpm nx affected -t lint
pnpm nx affected -t test
pnpm nx affected -t build

# Format
pnpm nx format:write
pnpm nx format:check

# Workspace
pnpm nx graph
pnpm nx show project <pkg>
pnpm nx show projects
pnpm nx sync

# Release
pnpm nx release --dry-run
pnpm nx release --first-release
pnpm nx release

# Local registry
pnpm nx local-registry
```

### Creating a package

1. `pnpm nx g <REDACTED_USER>/js:lib packages/<n> --bundler=none --unitTestRunner=vitest --publishable --importPath=<REDACTED_USER>/<n>`
2. Verify inferred targets: `pnpm nx show project <n>`
3. Configure `package.json` exports: `"type": "module"`, `"exports"` pointing to `dist/`
4. `pnpm install && pnpm nx sync`

### TypeScript Best Practices

- Use strict type checking (enabled in `tsconfig.base.json`)
- Prefer type inference when the type is obvious
- Avoid the `any` type; use `unknown` when type is uncertain
- Use `import type { ... }` for type-only imports
- ESM only — all packages use `"type": "module"`
- Use `isolatedModules`-compatible patterns (no const enums, no namespace merging)
- Prefer `interface` over `type` for object shapes (better error messages, extendable)
- Use `readonly` for properties that should not be reassigned
- Prefer `satisfies` operator over type assertion when validating shapes
- Do not use `<REDACTED_USER>` — use `<REDACTED_USER>` with explanation

### Code Style

- Keep functions small and focused on a single responsibility
- Use `const` by default, `let` only when reassignment is needed
- Prefer early returns over nested conditions
- Use descriptive names — avoid abbreviations except well-known ones (`ctx`, `req`, `res`)
- Co-locate tests with source (`*.spec.ts` next to `*.ts`)
- One export per file for main modules; barrel `index.ts` for package public API

### Commit Conventions

Format: `<type>(<scope>): <description>`

Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `ci`

Scopes: `repo`, `ci`, `deps` (extend in `commitlint.config.mjs` as packages are added)

Enforced by Lefthook + commitlint.

### Continue.dev (optional)

For dual-AI workflow (Claude Code generation + Gemini review), create `.continuerc.json`:

```json
{
  "models": [
    {
      "title": "Gemini 2.5 Pro",
      "provider": "google",
      "model": "gemini-2.5-pro",
      "apiKey": "${GOOGLE_API_KEY}"
    }
  ],
  "contextProviders": [
    { "name": "code" },
    { "name": "docs" },
    { "name": "diff" },
    { "name": "terminal" },
    { "name": "codebase" }
  ]
}
```

Requires `GOOGLE_API_KEY` in environment.