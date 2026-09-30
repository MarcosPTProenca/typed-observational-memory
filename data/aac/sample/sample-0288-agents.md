Please also reference the following rules as needed. The list below is provided in TOON format, and `@` stands for the project root directory.

rules[1]{path}:
  @.agents/memories/20-tooling.md

# Additional Conventions Beyond the Built-in Functions

As this project's AI coding tool, you must follow the additional conventions below, in addition to the built-in functions.

# dotnet-agent-harness

Comprehensive .NET development guidance for modern C#, ASP.NET Core, MAUI, Blazor, and cloud-native apps.

## RuleSync-first architecture

- `.rulesync/` is the source of truth for this repository's agent content. Author changes in `rules`, `skills`,
  `subagents`, `commands`, `hooks`, and `mcp` there first.
- Generated target directories and prompt files are build artifacts. Regenerate them from RuleSync instead of editing
  them by hand.
- Keep the shared root `AGENTS.md` content in this overview rule and keep follow-up split rules off AGENTS-writing
  targets so regeneration stays stable.
- Runtime commands, exported bundles, and published agent packs all inherit from the RuleSync-authored catalog. When
  generated output looks wrong, fix `.rulesync/` and re-run `rulesync`.

## Surface ownership

- `rules`: always-on repository guidance, routing, and cross-cutting constraints.
- `skills`: reusable domain knowledge and implementation standards.
- `subagents`: named specialists with bounded scope and tool budgets.
- `commands`: user-invocable entry points that should prefer the local runtime over hand-written procedures.
- `hooks`: ambient reminders and lightweight automation; keep them advisory and portable.
- `mcp`: shared MCP server registrations and transport metadata for targets that support MCP.

## Working contract

- Keep frontmatter strictly RuleSync-compliant and add target-specific blocks only for real runtime differences.
- Keep commands deterministic, keep hooks advisory, and route hook-only targets through generated rules or hook text
  instead of unavailable skill or command surfaces.
- Validate and regenerate with the system-wide `rulesync` binary: use `rulesync generate --check` as the consistency
  gate, then `rulesync generate` when changes are intentional.
- Review source and generated diffs together; do not hand-edit generated target directories to patch a platform quirk.
- **Verify target configurations** using the per-target checklists in `.rulesync/verification/` before committing changes.

## Platform model

This toolkit provides:

- 193 skills
- 18 specialist agents/subagents
- shared RuleSync rules, commands, hooks, and MCP config

Compatible targets include:

- Claude Code
- GitHub Copilot CLI
- OpenCode
- Codex CLI
- Gemini CLI
- Antigravity
- Factory Droid

Target support is intentionally asymmetric. Author the shared behavior once, then add target-specific blocks only where
the runtime surface actually differs.

## Quick Start

This toolkit is distributed via RuleSync. See project documentation for installation instructions.

## OpenCode behavior

- Tab cycles **primary** agents only.
- `<REDACTED_USER>` invokes subagents.
- `dotnet-architect` is configured as a primary OpenCode agent in this toolkit so it can appear in Tab rotation.



## Hook coverage

- Gemini CLI inherits the shared .NET session routing and now also receives the thin post-edit Roslyn, formatting, and
  Slopwatch advisories generated from `.rulesync/hooks.json`.
- Factory Droid consumes the same .NET session and MCP routing through generated rules and hooks, but its hook reminders
  stay compatible with that runtime's rules-plus-hooks surface instead of requiring imported skills or commands.

## Troubleshooting

If RuleSync reports `Multiple root rulesync rules found`, ensure only one root overview rule exists in
`.rulesync/rules/`.

Use RuleSync commands directly instead of manually reproducing catalog, prompt, incident, or graph logic from source
files.