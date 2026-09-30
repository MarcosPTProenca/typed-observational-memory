# Repository Guidelines

## Project Structure & Module Organization

- `src/main/java`: application sources. `Main.java` is the entry point (Java 25 compact source). `Calculator.java` and
  `CalculatorOperations.java` hold the logic.
- `src/test/java`: unit tests (JUnit 5). Empty now but reserved for new tests.
- `src/main/resources` and `src/test/resources`: non-code assets.
- Gradle wrapper and build files live at the repo root (`gradlew`, `gradle/`, `build.gradle`).

## Build, Test, and Development Commands

- `./gradlew run`: builds and runs the CLI calculator (reads from stdin).
- `./gradlew test`: runs JUnit 5 tests.
- `./gradlew build`: compiles and runs tests.
- `./gradlew clean`: removes build outputs.

## Coding Style & Naming Conventions

- Java, 4-space indentation, braces on the same line.
- Class names in PascalCase; methods/fields in lowerCamelCase.
- Keep source paths aligned with package names if you add packages.
- The app uses Java 25 `IO.readln/println`; avoid mixing `IO` with `Scanner`/`System.in` in the same flow.
- Encode files as UTF-8.

## Testing Guidelines

- Framework: JUnit Jupiter (JUnit 5).
- Name tests `*Test.java` (e.g., `CalculatorOperationsTest.java`).
- Keep tests focused and deterministic; prefer unit tests over console-driven tests.

## Commit & Pull Request Guidelines

- No strict commit convention in history. Use short, imperative summaries (e.g., "Fix division by zero handling").
- In PRs, include: what changed, why it changed, and how to run/verify (`./gradlew test` or `./gradlew run`).
- Call out any breaking behavior or input/UX changes.

## Configuration & Toolchain

- Java toolchain is pinned to 25 in Gradle; auto-download is enabled in `gradle.properties`.
- Keep IDE metadata and build outputs out of git (see `.gitignore`).