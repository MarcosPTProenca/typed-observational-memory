# [PROJECT_NAME] — Project Quick Reference

**Last Updated:** [DATE]

## Tech Stack

- **Language:** [LANGUAGE_AND_VERSION]
- **Framework:** [FRAMEWORK_AND_VERSION]
- **Backend:** [BACKEND_STACK] (if applicable)
- **Database:** [DATABASE] (if applicable)
- **Build System:** [BUILD_TOOL]
- **Package Manager:** [PACKAGE_MANAGER]

## Targets / Entry Points

| Target | Identifier | Environment | Command |
|--------|-----------|-------------|---------|
| App / Server | `[ID]` | [ENV] | `[COMMAND]` |
| Tests | `[ID]` | [ENV] | `[COMMAND]` |
| Linter | — | local | `[LINT_COMMAND]` |

## Directory Structure

```
[project-name]/
├── src/                  # Application source
│   ├── components/       # UI components (if applicable)
│   ├── services/         # Business logic / API clients
│   ├── models/           # Data models / types
│   └── utils/            # Shared utilities
├── scripts/              # Build and utility scripts
├── docs/                 # Documentation
├── .claude/
│   ├── rules/            # AI agent rules (this directory)
│   └── hooks/            # Auto-build and security hooks
└── [CONFIG_FILES]        # package.json, Cargo.toml, etc.
```

## Build Commands

```bash
# Development
[DEV_BUILD_COMMAND]

# Production
[PROD_BUILD_COMMAND]

# Lint / Type Check
[LINT_COMMAND]

# Run
[RUN_COMMAND]
```

## Key Constants

| Item | Value |
|------|-------|
| Default Port | `[PORT]` |
| API Prefix | `[API_PREFIX]` |
| Config Path | `[CONFIG_PATH]` |
| Log Location | `[LOG_PATH]` |

## Architecture Notes

<!-- Document key architectural decisions so the AI doesn't guess -->
- Navigation: [How routing/navigation works]
- State Management: [How state is managed]
- API Layer: [How API calls are structured]
- Authentication: [How auth works]
- Error Handling: [Error handling patterns]

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `[VAR_NAME]` | Yes/No | [Description] |