# GitHub Copilot Instructions — VIS42 MCP Bundle

## Project Overview

This repository produces `vis42.mcpb`, an MCP Bundle that installs into Claude Desktop with a single click. The bundle contains a Node.js stdio-to-HTTP proxy server that forwards all MCP operations to `https://vis42.com/api/mcp`.

Spec reference: [MCPB MANIFEST.md](https://github.com/anthropics/mcpb/blob/main/MANIFEST.md) | [Architecture overview](https://github.com/anthropics/mcpb/blob/main/README.md)

## Key Patterns

### Lazy Remote Connection (`server/index.js`)

The proxy must answer Claude Desktop's `initialize` immediately. Remote connection is deferred:

```js
// CORRECT — connect lazily on first request
async function getRemoteClient() {
  if (remoteClient) return remoteClient;
  if (connectPromise) return connectPromise;
  connectPromise = (async () => { /* connect, set remoteClient */ })();
  return connectPromise;
}

server.setRequestHandler(ListToolsRequestSchema, async (req) => {
  const client = await getRemoteClient(); // lazy
  return await client.listTools(req.params);
});
```

```js
// WRONG — never block in startup
await connectToRemote(); // this will timeout Claude Desktop
```

### SSE Transport Fallback

Transport **constructors never throw**. Errors surface only when `client.connect()` is awaited. The SSE fallback must wrap the `connect()` call:

```js
// CORRECT — fallback wraps connect(), not the constructor
const transport = new StreamableHTTPClientTransport(url, { requestInit: { headers } });
try {
  await client.connect(transport);
} catch (err) {
  log(`StreamableHTTP failed (${err.message}), retrying with SSE...`);
  const sseTransport = new SSEClientTransport(url, { requestInit: { headers } });
  await client.connect(sseTransport); // let this throw naturally if SSE also fails
}

// WRONG — constructor never throws, catch never activates
try {
  transport = new StreamableHTTPClientTransport(url, opts);
} catch (err) {
  transport = new SSEClientTransport(url, opts); // dead code
}
await client.connect(transport);
```

### Logging

All log output must go to `stderr`. `stdout` is the MCP protocol channel.

```js
// CORRECT
const log = (msg) => process.stderr.write(`[vis42-proxy] ${msg}\n`);

// WRONG — corrupts MCP protocol
console.log("debug info");
```

### manifest.json — Tools

Tools are stripped to `{ name, description }` only. The upstream payload includes runtime hints that must not appear in the manifest:

```js
// CORRECT
const tools = rawTools.map(t => ({ name: t.name, description: t.description }));

// WRONG — readOnlyHint and other hints are not valid manifest fields
const tools = rawTools.map(t => ({ name: t.name, description: t.description, readOnlyHint: t.readOnlyHint }));
```

### manifest.json — Prompts

Prompt arguments in the manifest are string names, not objects:

```js
// CORRECT — manifest spec: arguments is string[]
const prompts = rawPrompts.map(p => ({
  name: p.name,
  description: p.description,
  ...(p.arguments?.length && { arguments: p.arguments.map(a => a.name) }),
}));

// WRONG — objects are not valid in manifest prompts.arguments
const prompts = rawPrompts.map(p => ({ ...p })); // keeps { name, description, required } objects
```

### manifest.json — Resources

`resources` is **not a valid manifest field**. The pack validator rejects it.

```js
// CORRECT — skip resources entirely for manifest
const resourceCount = rawResources.length; // log only

// WRONG — pack will fail: "Unrecognized key(s) in object: 'resources'"
manifest.resources = rawResources;
```

Resources are handled at runtime by the proxy's existing `resources/list`, `resources/read`, and `resources/templates/list` handlers.

### Null-safe payload parsing (CI workflow)

The `toJSON()` expression in GitHub Actions produces `"null"` for absent fields:

```js
// CORRECT — handles absent/null payload fields
const raw = JSON.parse(process.env.SOME_JSON || 'null') || [];

// WRONG — crashes when field is absent from payload
const raw = JSON.parse(process.env.SOME_JSON);
```

### GitHub Actions — payload security

Use `env:` variables for all payload data. Never interpolate `client_payload` fields directly in `run:` scripts:

```yaml
# CORRECT
- run: node -e "const data = JSON.parse(process.env.DATA); ..."
  env:
    DATA: ${{ toJSON(github.event.client_payload.tools) }}

# WRONG — direct interpolation is an injection risk
- run: echo "${{ github.event.client_payload.tools }}"
```

## manifest.json Field Reference

| Field | Type | Maintained by | Notes |
|---|---|---|---|
| `manifest_version` | `"0.3"` | Manual | Do not change |
| `name` | string | Manual | Machine-readable ID |
| `version` | string | CI | Synced with `server/package.json` |
| `tools` | `{name, description}[]` | CI | Stripped from upstream payload |
| `prompts` | `{name, description, arguments?}[]` | CI | Arguments as string names |
| `resources` | — | **Never** | Not in schema; proxy handles at runtime |
| `tools_generated` | boolean | Manual | Omit or set false for static tools |
| `prompts_generated` | boolean | Manual | Omit or set false for static prompts |
| `user_config` | object | Manual | `api_token` injected as `VIS42_API_TOKEN` |
| `compatibility` | object | Manual | `claude_desktop >= 0.10.0`, `node >= 18`, `darwin` + `win32` |

## Version Synchronisation

Two files must always have the same semver version:
- `manifest.json` → `.version`
- `server/package.json` → `.version`

CI writes both atomically. When editing manually, update both.

## CI Trigger

The workflow `sync-tools.yml` listens for:
```yaml
on:
  repository_dispatch:
    types: [sync_mcp_server]   # underscore, not hyphen
```

## Build and Test

```bash
# Run unit tests
cd server && npm test

# Validate manifest and produce vis42.mcpb
npx <REDACTED_USER>/mcpb pack .

# Install server dependencies (mirrors CI)
cd server && npm install --production
```

Install the resulting `vis42.mcpb` into Claude Desktop → Settings → Extensions to test end-to-end.