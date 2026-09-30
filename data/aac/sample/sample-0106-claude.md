# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an n8n community node package that provides Excel file operations for SharePoint via Microsoft Graph API. Unlike native n8n SharePoint nodes that use WAC (Web Application Companion) tokens for Excel operations, this node downloads/uploads the entire Excel file using the `exceljs` library, bypassing WAC token limitations.

## Commands

```bash
bun run build        # Compile TypeScript to dist/
bun run lint         # Typecheck + n8n ESLint + Prettier check
bun run lint:fix     # Auto-fix linting + format code (USE THIS)
bun run test         # Run tests with vitest (DO NOT use `bun test`)
bun run dev          # Start n8n with node loaded + hot reload (DO NOT run this)
```

**Important:** Use `bun run test` not `bun test`. The latter uses Bun's built-in test runner which doesn't support vitest APIs like `vi.mocked()`.

## Tooling

- **ESLint** - n8n-specific linting rules via `n8n-node lint`
- **Prettier** - Code formatting
- **Husky** - Git hooks for pre-commit and commit-msg
- **Commitlint** - Enforces conventional commit format

### Commit Convention

Commits must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

# Examples:
feat(node): add delete row operation
fix(auth): handle token refresh error
```

## Architecture

### Node Structure

- **`nodes/SharePointExcel/SharePointExcel.node.ts`** - Main node implementing `INodeType`
- **`credentials/MicrosoftGraphOAuth2Api.credentials.ts`** - Generic Microsoft Graph OAuth2 credential

### How It Works

The node uses a download-modify-upload pattern (bypasses WAC token issues):

1. Downloads Excel file via Graph API (`GET .../content`)
2. Parses with `exceljs` library
3. Performs operation (read/write)
4. Uploads modified file back (`PUT .../content`)

API endpoint:

- SharePoint: `/sites/{siteId}/drives/{driveId}/items/{fileId}/content`

### Operations

- `getSheets` - List worksheets in workbook
- `readRows` - Read rows with configurable header/start row
- `appendRows` - Add rows matching existing headers
- `updateCell` - Update single cell by reference (e.g., A1)

### Required IDs

- `siteId` - SharePoint site (format: `hostname,site-guid,web-guid`)
- `driveId` - Drive ID (format: `b!xxxxx`)
- `fileId` - Excel file item ID

### n8n Registration

Nodes and credentials are registered in `package.json` under the `n8n` field pointing to compiled `dist/` files.