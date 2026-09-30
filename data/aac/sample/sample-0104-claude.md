# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository builds an n8n community node for VNTANA's 3D content management platform. The goal is to enable n8n workflows to interact with VNTANA's Admin API for managing 3D products, organizations, and workspaces.

**Scope:** Minimal MVP focusing on Products and Authentication operations.

## Architecture

### Target Structure
```
n8n-nodes-vntana/
├── package.json
├── nodes/
│   └── Vntana/
│       ├── Vntana.node.ts        # Main node (declarative style)
│       ├── Vntana.node.json      # Codex metadata
│       └── vntana.svg            # Node icon
└── credentials/
    └── VntanaApi.credentials.ts  # Auth configuration
```

### Node Style
Use **declarative style** - JSON-based routing instead of `execute()` method. This is recommended for REST APIs and is more future-proof.

## VNTANA API Details

**Base URL:** `https://api-platform.vntana.com`

**Authentication:** Header-based using `X-AUTH-TOKEN`
- VNTANA uses two-step auth: login → refresh-token with organizationUuid
- For n8n, store the org-specific token directly in credentials

**Key Endpoints for MVP:**
| Operation | Method | Endpoint |
|-----------|--------|----------|
| Get Product | GET | `/v1/products/{uuid}` |
| Search Products | POST | `/v1/products/clients/search` |
| Update Product | PUT | `/v1/products` |
| Delete Product | DELETE | `/v1/products/delete` |
| Update Status | PUT | `/v1/products/status` |
| List Organizations | GET | `/v1/organizations` |
| List Workspaces | GET | `/v1/clients/client-organizations` |

**Response Format:** All responses use `{ success: boolean, errors: [], response: {...} }`

## Commands

```bash
# Build
npm run build              # tsc && gulp build:icons

# Development
npm run dev                # tsc --watch

# Lint
npm run lint               # eslint nodes credentials --ext .ts
npm run lintfix            # eslint with --fix

# Local testing
npm link                   # After build
cd ~/.n8n/custom && npm link n8n-nodes-vntana
n8n start
```

## Testing Workflow

**IMPORTANT:** Before asking the user to test in n8n, verify the implementation works:

### 1. Write Unit Tests
All new operations must have unit tests. Run tests before any manual testing:
```bash
npm test
```

### 2. Test with curl First
If it doesn't work with curl, it won't work with n8n. Always verify API calls work:

```bash
# Template for VNTANA API calls
curl -X POST "https://api-platform.vntana.com/v1/<endpoint>" \
  -H "Content-Type: application/json" \
  -H "X-AUTH-TOKEN: Bearer <token>" \
  -d '<json-body>'
```

### 3. Build and Relink
```bash
npm run build
<REDACTED_USERPATH>/GitHub/VNTANA-n8n-node/.claude/skills/n8n-relink/scripts/relink.sh
```

### 4. Have User Test in n8n
Only after curl verification succeeds.

## Versioning Rules

**IMPORTANT:** Always bump the version when committing changes to node code (`nodes/` or `credentials/`).

### When to Bump Version

| Change Type | Bump? | Version Type |
|-------------|-------|--------------|
| New operation/feature in node | ✅ Yes | `patch` or `minor` |
| Bug fix in node code | ✅ Yes | `patch` |
| Breaking API changes | ✅ Yes | `major` |
| Test-only changes (no node code) | ❌ No | - |
| Documentation-only changes | ❌ No | - |
| CI/CD workflow changes | ❌ No | - |

### Version Bump Workflow

When committing changes that affect `nodes/` or `credentials/`:

```bash
# 1. Run tests first
npm test

# 2. Bump version (this creates a commit and tag)
npm version patch   # Bug fixes, small features
npm version minor   # New operations, significant features
npm version major   # Breaking changes

# 3. Push with tags
git push origin main --tags

# 4. Publish to npm
npm publish
```

### Commit Without Publishing

If you need to commit node changes but defer publishing:
1. Make your changes and commit them
2. Before the next publish, bump version to cover all changes since last release
3. Then publish

## Publishing to npm

### Pre-publish Checklist

1. **GitHub repo must be public** - n8n verifies the repo exists and checks for credential files
2. **Run the scanner locally first:**
   ```bash
   npx <REDACTED_USER>/scan-community-package n8n-nodes-vntana@latest
   ```
3. **All code must use `httpRequest`** - The deprecated `this.helpers.request()` is not allowed

### Publishing Steps

```bash
# 1. Build and verify
npm run build

# 2. Bump version (creates commit + tag)
npm version patch   # or minor/major

# 3. Push to GitHub with tags
git push origin main --tags

# 4. Publish to npm
npm publish

# 5. Verify with scanner (use explicit version to avoid cache)
npx <REDACTED_USER>/scan-community-package n8n-nodes-vntana@<new-version>
```

### Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| "GitHub repo appears invalid" | Repo is private | Make repo public |
| "Can't find credential file" | Repo private or path wrong | Verify `credentials/` exists in repo |
| "ESLint: 'request' is deprecated" | Using `this.helpers.request()` | Use `httpRequest` instead |
| Scanner shows old version | npm cache | Specify version explicitly: `<REDACTED_USER>.1.1` |

### httpRequest in Credential Tests

n8n's `ICredentialTestFunctions.helpers` doesn't expose `httpRequest` in types, but it exists at runtime. Use type assertion:

```typescript
const helpers = this.helpers as unknown as { httpRequest: (options: object) => Promise<any> };
const response = await helpers.httpRequest({
    method: 'POST',
    url: 'https://api.example.com/auth',
    body: { email, password },
    returnFullResponse: true,  // NOT resolveWithFullResponse
});
```

## Reference Documentation

Detailed API and n8n docs are in `documentation/`:
- `documentation/vntana-api-docs/CLAUDE.md` - Full VNTANA API reference
- `documentation/n8n-docs/CLAUDE.md` - n8n node development patterns
- `documentation/vntana-api-docs/swagger/` - OpenAPI specs (237 Admin API endpoints)