# Repository Guidelines

## Project Structure & Module Organization
Core Gatsby code lives in `src/`: keep routed pages in `src/pages`, reusable UI in `src/components`, templates consumed by `gatsby-node.js` under `src/templates`, and helper logic in `src/utils`. Editorial content sits in `content/blog/<slug>/index.mdx` with related media under `content/assets`. Assets that must ship verbatim belong in `static/` (including the Decap CMS admin) while site wiring stays in `gatsby-config.js` and `gatsby-node.js`.

## Build, Test, and Development Commands
Use `nvm use 18.20.2` plus `yarn install` to match the toolchain. `yarn develop` serves the site on http://localhost:8000 with hot reload; leave it running while you edit MDX or components. `yarn build` compiles the static bundle to `public/` and should run clean before every pull request. Reach for `yarn serve` to preview that bundle and `yarn clean` if caches misbehave; `yarn format` runs Prettier locally.

## Coding Style & Naming Conventions
Prettier handles formatting (2-space indents, double quotes, no semicolons, ES5 trailing commas, LF endings); run `yarn format` before committing. Components should remain functional React, exported as PascalCase even when filenames follow the established lowerCamelCase pattern (`navbarLinks.js` -> `NavbarLinks`). Prefer co-locating styling with `styled-components`, keep shared tokens in `src/styles`, and name utilities in camelCase within `src/utils`.

## Testing Guidelines
There is no automated suite yet, so treat `yarn build` as the smoke test gate. While developing, manually verify primary routes (`/`, `/blog/<slug>`) and confirm MDX frontmatter resolves images from `content/assets`. If you add behavior-heavy utilities, drop Jest specs in a mirrored path under `src/__tests__/` to ease future maintenance.

## Commit & Pull Request Guidelines
Commits follow an imperative, concise subject style (`Add link to adsnap.eu`, `Fix sitemap`). Work on focused branches such as `feature/<slug>` or `fix/<area>` and rebase before opening a pull request. PR descriptions should summarize intent, link any issues, enumerate manual checks, and attach UI screenshots when visuals change. Wait for Netlify deploy previews and the CodeQL workflow to pass; note exceptions explicitly.

## Security & Automation Notes
CodeQL (`.github/workflows/codeql-analysis.yml`) scans JavaScript on pushes and pull requests to `master`; investigate alerts promptly and keep the workflow green. Never commit secrets; load API keys via environment variables configured in Netlify or local `.env` files already ignored.