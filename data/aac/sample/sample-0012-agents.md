# Agents

This is a personal knowledge base for infrastructure, server setup and CLI workflows.
Target system: Debian / Ubuntu.

## Structure

- `guides/` – step-by-step instructions (runbook-style)
- `cheatsheets/` – quick-reference commands
- `templates/` – copy-paste-ready config files (.bashrc, Makefile, docker-compose.yml, nginx.conf)
- `scripts/` – reusable bash scripts
- `theory/` – conceptual reference material (German, imported from another project)

## Language

All documentation is written in English. Keep it that way.

**Exception:** Files in `theory/` are written in German. These were imported from another project and will stay in German. Do not translate them.

## Commands

| Command | Description |
|---------|------------|
| `grep -r '<term>' .` | Search for references across all files |
| `find . -name '*.md'` | List all Markdown files |

## Boundaries

- ✅ **Always:** Update `README.md` when adding, removing or renaming files
- ✅ **Always:** Cross-reference instead of duplicating content
- ✅ **Always:** Verify links after renaming or deleting a file
- ⚠️ **Ask first:** Deleting a file (check for references first)
- ⚠️ **Ask first:** Renaming a file (update all references)
- 🚫 **Never:** Duplicate content across files
- 🚫 **Never:** Write content in a language other than English
- 🚫 **Never:** Leave dead links in the repository

## Conventions

- Read `README.md` for a full index of all files before making changes.
- Before editing or creating a file, read the target directory to understand existing content and style.
- Keep files concise and practical – no boilerplate prose. Optimise for fast scanning.
- Guides use fenced code blocks with copy-paste-ready commands and `diff` blocks for config changes.
- Cheatsheets use tables or commented code blocks – no explanatory paragraphs.
- Templates must be functional as-is, with commented-out optional sections.
- Update `README.md` when adding, removing or renaming files.

## Workflow

For multi-file changes, follow the **plan-first** principle:

1. **Research** — read affected files, understand existing style and cross-references.
2. **Plan** — create `plan.md` in the project root with goal, affected files, and a step-by-step checklist. Do not make changes yet.
3. **Execute** — work through the checklist one step at a time. Tick off each step (`- [x]`) immediately after completing it.
4. **Verify** — after all steps: check links (`grep -r '<filename>'`), confirm `README.md` is up to date, re-read changed files for consistency.
5. **Clean up** — delete `plan.md` when done.

Use the `/plan` prompt to generate a plan. For trivial single-file changes (typo fix, adding one section), skip the plan and edit directly.

## Keeping Docs in Sync

Every change must leave the knowledge base consistent. Follow these rules:

- **Single source of truth** – never duplicate content across files. If something is defined in a template or script, reference it from guides instead of copying it inline.
- **Cross-references over copies** – use relative links (`[docker-compose.prod.yml](templates/docker-compose.prod.yml)`) instead of repeating config blocks.
- **Delete, don't deprecate** – if a file becomes redundant, delete it and remove all references.
- **Version consistency** – when a tool version changes (Docker image tag, Node version, action version), grep the whole repo and update every occurrence.
- **README is the index** – it must always reflect the exact files on disk. After any file add/remove/rename, verify the table entries match.
- **No dead links** – after renaming or deleting a file, search for all references (`grep -r '<filename>'`) and update or remove them.
- **English only** – all content, examples and placeholder data must be in English.