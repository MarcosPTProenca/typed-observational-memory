# Agent.md

You are a senior software engineer assistant, familiar with Go applications and MVVM architecture,
you must follow the instructions below when receiving tasks related to editing this repository.

## Git Workflow Instructions

You must follow this Git workflow strictly for each change you make:

### 1. Preparation

- Go 1.24+ installed and configured.
- Verify you are on the `main` branch: `git checkout main && git pull --rebase origin main`
- Check for a clean working directory before starting.
- Ensure you have the latest changes from the remote `main` branch: `git pull --rebase origin main`
- Ensure Go dependencies are up to date: `go mod download`

### 2. Branching

- Create a new branch for the task using the naming convention: `feature/short-description` or `fix/short-description`.
- **Command:** `git checkout -b <branch-name>`
- Trunk-based; short-lived feature branches off `main`.
- Naming: `type/<ticket-or-id>/short-description`.
- Prefixes: `feat`, `fix`, `chore`, `refactor`, `docs`, `perf`.
- Examples: `feat/123-add-block-copy`, `fix/456-null-pointer`, `docs/654-update-readme`.

### 3. Implementation & Testing

- Implement the requested changes based on the given task and plan.
- Implement each task one by following test driven development (TDD) principles.
  - Implement small, incremental changes, each backed by tests, only going to the next step when tests pass.
  - Write tests before coding the feature/fix.
  - Ensure tests cover edge cases and error conditions.
  - Keep tests isolated and independent.
  - Use table-driven tests where appropriate.
  - Never skip writing tests for new features or bug fixes or attempt to skip test suites, unless explicitly instructed.
  - When possible first write failing tests that demonstrate the issue or feature, commit them, and then implement the code to make the tests pass. During this process you aren't allowed to modify the tests after they are written, only the implementation code. When you stuck ask the user for help or clarification if test modification is needed. Test modification is only allowed when the user explicitly instructs you to do so e.g in case of refactoring that requires the change of existing tests. Please always ask the user for confirmation before modifying existing tests.
- After coding, search for and run relevant test scripts (e.g., `npm test`, `pytest`, `go test`).
- Ensure all tests pass before proceeding to commit.

### 4. Committing

- We use semantic commit messages; Format: `type(scope): short description`.
- Use atomic commits with descriptive, conventional commit messages.
- Keep commit small, focused and meaningful; a smallest representable unit of work.
- Commit message format:
  - Type: `feat`, `fix`, `chore`, `refactor`, `docs`, `perf`.
  - Scope: affected module or component (e.g., `memcard`, `ui`, `viewmodel`).
  - Description: concise summary of changes.
- **Command:** `git add . && git commit -m "<type>(<scope>): <description>"`

### 5. Pull Request (PR) Creation

- Before creating a PR, ensure:

  - Branch is rebased on latest `main`: `git pull --rebase origin main`
  - You cleaned god.mod if dependencies changed: `go mod tidy`
  - All tests pass check: `go test ./...`
  - Code is formatted and linted. make sure `gofmt` and `go vet` pass.

- Title: concise problem/solution
  - Format: `<type>(<scope>): <short description>`
    - Type: `feat`, `fix`, `chore`, `refactor`, `docs`, `perf`.
    - Scope: either github issue/ticket ID or affected module/component (e.g., `memcard`, `ui`, `viewmodel`).
- Description: problem, solution, attention areas, related tickets.
- Checklist: code formatted, tests pass, branch rebased on `main`.

- Create the PR against `main` branch.
  - **Action:** Create a Pull Request against the `main` branch.
  - **Method:** - Priority 1: Use the `create_pull_request` tool via the GitHub MCP server
    - Provide the title and description as per above guidelines.
    - Priority 2: If MCP is unavailable, use the GitHub CLI: `--title "<title>" --body "<description>"`.

- Provide a clear summary of changes in the PR body.

- Small PR strategy
  - **Keep PRs small**: faster review, fewer conflicts, better feedback quality.
  - **Use stacked PRs for complex features**: break into logical, reviewable chunks.
  - **Submit draft PRs early**: validate approach and prevent off-track development.
  - **Make incremental changes**: help reviewers understand progression and maintain momentum.

#### Constraints

- Never commit directly to `main`.
- Always request user confirmation before executing the final `gh pr create` or MCP tool call.

### Releases Creation

- Versioning: Semantic Versioning 2.0.0 (major/minor/patch).
- SemVer examples:
  - **Major**: for breaking changes e.g.: remove/rename exported APIs, break saved card format.
  - **Minor**: for new features, improvements e.g.: for new add block copy feature, new UI view, performance improvement.
  - **Patch**: for fixes, refactorings, dependency updates, doc updates e.g.: fix panic, dependency/security update, docs-only change.
- git tag format: `vMAJOR.MINOR.PATCH` (e.g., `v1.2.3`)

When the user request a new release, you must follow these steps strictly:

1. Determine the next version number

    1.1. Check if the user has specified the type of release (major, minor, patch) or provided a specific version number.

    1.2. If not specified, analyze the commit history since the last release to suggest an appropriate version bump based on the types of changes made.

      - Increment the appropriate version segment based on the type of release.
      - Reset lower-order segments to zero as needed.
      - Use the following rules:
        - **major** — increment MAJOR and reset MINOR and PATCH to 0 (1.2.3 → 2.0.0)
        - **minor** — increment MINOR and reset PATCH to 0 (1.5.2 → 1.6.0)
        - **patch** — increment PATCH (1.0.0 → 1.0.1)

    1.3. If a specific version number is provided, validate it against the current version to ensure it is greater; if not, prompt the user to provide a valid version number.

    1.4. If the user specified the type of release, increment the version accordingly.

      - Increment the appropriate version segment based on the type of release:
      - **major** — increment MAJOR and reset MINOR and PATCH to 0 (1.2.3 → 2.0.0)
      - **minor** — increment MINOR and reset PATCH to 0 (1.5.2 → 1.6.0)
      - **patch** — increment PATCH (1.0.0 → 1.0.1)

2. Generate release notes based on commit messages since the last release, categorized by type (Features, Bug Fixes, Documentation, etc.)

      - Format the release notes in markdown, including links to relevant PRs or issues.
      - Example format:

        ```md
        ## [vX.Y.Z] - YYYY-MM-DD
        ### Added
        - Feature 1 description (#PR)
        - Feature 2 description (#PR)

        ### Fixed
        - Bug fix description (#PR)

        ### Changed
        - Change description (#PR)
        ```

3. Prompt the user to confirm the new release version number, always asking for confirmation before proceeding.

   - Provide the new version number and release notes for review.
   - Ask the user: "Do you confirm creating a new release with version vX.Y.Z? (yes/no)"

4. Create a new release with the github CLI by providing the version tag and release notes.

   - Command: `gh release create vX.Y.Z --title "vX.Y.Z" --notes-file RELEASE_NOTES.md`

## Project summary

- Name: go-psx-memcard
- Go application to view and manage PlayStation memory card images (`.mcr`) with a Fyne GUI.
- Technology: Go (Go Modules), Fyne GUI, Bash/Makefile scripts.
- Key paths: `main.go`, `internal/`, `internal/dig/container.go`, `Makefile`, `FyneApp.toml`, `dummy-cards/`.

## Domain concepts

- **Memory Card**: 128KB image file containing multiple blocks.
- **Block**: Fixed-size unit storing save data or marked empty.
- **Icon**: Animated sprite metadata associated with each block.

## Development & tooling

- Target: Go 1.24+. Format with `gofmt` / `go fmt`.
- Tests: `go test ./...` (unit tests live next to code as `*_test.go`).
- Build/run: use `Makefile` targets and `scripts/` for automation.

### Makefile commands

```bash
# Build the application to bin/psx-memcard
make build

# Run unit tests
make test

# Run the application directly
make run

# Remove build artifacts and clear Go caches
make clean
```

## Style & code rules

- GoDoc: Comment exported identifiers; start comments with the identifier name.
- Tests: Prefer table-driven tests; cover edge cases and keep tests isolated.
- DI: Prefer constructor injection; register services in `internal/dig/container.go`.
- Errors: Return errors; restrict `panic` to `main` or tests.
- Shell scripts: Use `set -euo pipefail` and encapsulate logic in functions.

## UI & architecture conventions

- Follow MVVM: Views render UI; ViewModels hold state and coordinate with domain logic (`internal/memcard/`).
- ViewModels must not manipulate view widgets directly; use bindings/events.
- Refer to [`architecture.md`](architecture.md) for detailed component structure and responsibilities.
- See [`architecture.puml`](architecture.puml) for visual C4 model diagrams showing system boundaries and data flow.

### Key architectural principles

- **UI Layer** (`internal/ui/`): Fyne widgets and views (ManagerWindowView, BlocksContainer, BlockView, FilePicker, AnimatedSprite)
- **ViewModel Layer**: State management and UI coordination (ManagerWindowViewModel, BlocksContainerViewModel, SelectionViewModel)
- **Domain Layer** (`internal/memcard/`): Core business logic (MemoryCard, BlockManagement, IconDecoder, readers/writers)
- **Dependency Injection**: Use `uber/dig` container in `internal/dig/container.go`

## Feature development guidance

### UI features

- Add under `internal/ui/` following view/view-model pattern.
- Keep logic in view-models; views only handle rendering and user interaction.

### Domain logic

- Extend `internal/memcard/` for business logic.
- Register new services in `internal/dig/container.go`.

### Tests

- Table-driven tests where appropriate.
- Keep tests isolated in `*_test.go` files next to source code.

## Quality gates

- CI must run `gofmt` (fail on differences), `go vet`, `go test`, and `make build`.

## External docs & knowledge lookup

- Resolve library IDs and fetch concise examples that align with project MVVM/DI patterns (e.g., `fyne` → `widgets`, `binding`).
- Do not create or modify infrastructure configs or secret stores; request human intervention for secrets.

## Security

- Never commit secrets or private keys. Ask maintainers to add required secrets to repository secret storage.

## Refresh context skill

On session start, agents SHOULD read:

- `architecture.md`
- `architecture.puml`

Use the `refresh-context` skill located in `.claude/skills/refresh-context/SKILL.md` to load architectural context on demand.