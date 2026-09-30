# Documentation project instructions

## About this project

- This is a documentation site built on [Mintlify](https://mintlify.com)
- Pages are MDX files with YAML frontmatter
- Configuration lives in `docs.json`
- Run `mint dev` to preview locally
- Run `mint broken-links` to check links

## Terminology

**Daytona-specific terms:**
- **Sandbox** - Isolated execution environment for running code
- **Snapshot** - Pre-built environment template for fast sandbox creation
- **Volume** - Persistent storage that survives sandbox lifecycle
- **Toolbox API** - Internal API running inside sandboxes

## Style preferences

- Use active voice and second person ("you")
- Keep sentences concise — one idea per sentence
- Use sentence case for headings
- Bold for UI elements: Click **Settings**
- Code formatting for file names, commands, paths, and code references

## Content boundaries

**Documented:**
- SDK usage (Python, TypeScript, Go, Ruby)
- CLI commands
- REST API endpoints
- Core concepts and architecture
- Integration guides and examples

**Not documented:**
- Internal admin features
- Private API endpoints
- Development-only tools