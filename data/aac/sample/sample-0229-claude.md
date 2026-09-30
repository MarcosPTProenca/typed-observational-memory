# Go AST Inspector - AI Agent Instructions

This file contains important information that AI agents (such as Claude Code) should reference when working on this project.

---

## Project Overview

**Go AST Inspector** is a standalone tool that extracts Abstract Syntax Trees (AST) from Go language source code and visualizes them intuitively in a browser.

- **Distribution Format**: Distributable as a single HTML file
- **Key Technologies**: TypeScript, Svelte 5.x, Go WebAssembly, Vite
- **Target Users**: Professional Go language developers

---

## Important Documents

Before working on the project, please refer to the following documents:

### 1. [REQUIREMENTS.md](./REQUIREMENTS.md)
- **Contents**: Project requirements specification
- **Reference Timing**: When understanding the overall project, when checking functional requirements
- **Key Sections**:
  - Functional Requirements (FR-001 to FR-006)
  - Non-functional Requirements (NFR-001 to NFR-006)
  - Technology Selection Decisions
  - MVP Scope Definition

### 2. [DESIGN.md](./DESIGN.md)
- **Contents**: Technical design document
- **Reference Timing**: Before starting implementation, when understanding architecture
- **Key Sections**:
  - Technology Stack
  - Architecture Design (3-layer structure)
  - Module Design and Directory Structure
  - Svelte Component Design
  - Build Configuration (Vite, TypeScript, Biome, Svelte)
  - Data Flow Design

---

## Before Starting Work

### Required Checks

1. **Read REQUIREMENTS.md**
   - Understand project objectives and requirements
   - Check MVP scope (FR-001 to FR-006)
   - Understand technology selections (Svelte 5.x, TypeScript, WebAssembly)

2. **Read DESIGN.md**
   - Understand architecture (WebAssembly Layer, Application Logic Layer, UI Layer)
   - Check directory structure
   - Understand state management design using Svelte Store

### Recommended Workflow

```
1. REQUIREMENTS.md → Project Understanding
2. DESIGN.md → Architecture and Technical Specification Understanding
3. Implementation → Implement according to design
```

---

## Technology Stack Highlights

### Frontend
- **Language**: TypeScript 5.x (strict mode)
- **UI Framework**: Svelte 5.x (runes mode enabled)
- **Build Tool**: Vite 5.x
- **Linter/Formatter**: Biome 1.x
- **UI Language**: English only

### Backend (WebAssembly)
- **Language**: Go 1.21+
- **Packages**: go/ast, go/parser, go/token

### State Management
- **Method**: Svelte Writable Store
- **Main Stores**:
  - `astStore`: AST state
  - `parseErrorStore`: Parse errors
  - `selectedNodeStore`: Selected node
  - `expandedNodesStore`: Expanded nodes

---

## Coding Conventions

### TypeScript
- Enable strict mode
- Explicitly write type definitions
- Avoid magic numbers, use constants

### Svelte
- Use Svelte 5 runes mode (`$state`, `$derived`, `$effect`)
- Components follow single responsibility principle
- Explicitly type props

### Styling
- BEM naming convention recommended
- Global styles in `src/styles/global.css`
- Component-specific styles in `<style>` section

### Comments
- MUST convention: Prohibit redundant comments (no explanation needed for simple operations)
- SHOULD convention: Write comments where code intent is hard to convey

### Commit and Pull Request
- MUST convention: Write commit messages in English
- MUST convention: Write Pull Request titles and descriptions in English
- MUST convention: Add GPG sign to all commits
- MUST convention: Add Claude as Co-Author:
  ```
  🤖 Generated with [Claude Code](https://claude.com/claude-code)
  
  Co-Authored-By: Claude <<REDACTED_EMAIL>>
  ```

### Pre-commit Checks
- MUST convention: Run `npm run lint` before committing
- MUST convention: Run `npm run type-check` before committing
- If either command exits with an error, fix the issues before committing
- Common fixes:
  - Lint errors: Run `npm run format` to auto-fix formatting issues
  - Type errors: Fix type mismatches in the reported files

---

## Frequently Asked Questions

### Q: Why use Svelte instead of Vanilla JavaScript?
A: For bundle size minimization, reactive state management, and maintainability. See "Rejected Technologies and Reasons" in DESIGN.md.

### Q: Where is WebAssembly used?
A: Only for Go language AST analysis. Use go/parser to convert source code to AST.

### Q: How is it embedded in a single HTML file?
A: Using Vite's vite-plugin-singlefile. All JS/CSS/WASM binaries are inlined.

### Q: Are tests mandatory?
A: Not included in MVP, but recommended for quality assurance.

---

## Troubleshooting

### If you find contradictions between documents
1. Priority order: REQUIREMENTS.md > DESIGN.md
2. Report contradictions to user and request confirmation

### If there are unclear specifications
1. First check REQUIREMENTS.md and DESIGN.md
2. Ask user if not documented
3. Do not implement based on independent judgment

### If build errors occur
1. Check build configuration in DESIGN.md
2. Check package.json dependencies
3. Analyze error messages in detail

---

## Related Links

- [Svelte Documentation](https://svelte.dev/)
- [Svelte 5 Runes](https://svelte.dev/docs/svelte/what-are-runes)
- [Vite Documentation](https://vitejs.dev/)
- [Biome Documentation](https://biomejs.dev/)
- [Go WebAssembly](https://github.com/golang/go/wiki/WebAssembly)

---

**Last Updated**: 2025-11-30  
**Version**: 1.2