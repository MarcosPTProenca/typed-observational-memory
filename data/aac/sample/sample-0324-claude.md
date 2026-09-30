# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Java learning examples repository focused on Java 21 with Gradle 8 as the build system. The project is designed for educational purposes with simple, standalone Java examples organized in folders.

## Build System & Commands

The project uses **Gradle with wrapper** (always use `./gradlew`):

### Core Build Commands

```bash
# Build project (skip tests)
./gradlew build -x test

# Run tests
./gradlew test

# Clean build artifacts
./gradlew clean
```

### Running Examples

The project has custom Gradle tasks for running Java examples:

```bash
# List all available examples
./gradlew listExamples
./gradlew listSimple  # Simplified format

# Run specific example by full class name
./gradlew runExample --args="intro.lesson01.WelcomeToJava"

# Run example by folder/filename (simpler approach)
./gradlew runSimple -Pexample=01_intro/WelcomeToJava

# Quick compile and run (bypass package structure)
./gradlew quickRun -PclassName=WelcomeToJava
```

### Code Quality & Linting Commands

```bash
# Run all linting and code quality checks
./gradlew lint

# Individual quality checks
./gradlew checkstyleMain  # Google Java Style checks
./gradlew pmdMain         # Static analysis  
./gradlew spotbugsMain    # Bug detection

# Format code (built into Gradle - no external dependencies)
./gradlew format          # Auto-format with Google Java Style

# Run all checks before committing
./gradlew preCommit       # Runs build, lint, and test
```

### Makefile Shortcuts

The project includes a Makefile for common tasks:

```bash
make build     # ./gradlew build -x test
make test      # ./gradlew test
make clean     # ./gradlew clean
make lint      # ./gradlew lint
make format    # ./gradlew format
make precommit # ./gradlew preCommit
```

## Code Architecture

### Directory Structure

- **Non-standard source layout**: Uses `src/` as root instead of `src/main/java/`
- **Flat package structure**: Classes are in folders without package declarations
- **Example-based organization**: Each folder (`01_intro/`, `02_otherExample/`) contains standalone examples

### Source Configuration

The `build.gradle` customizes source sets:

```gradle
sourceSets {
    main {
        java {
            srcDirs = ['src']
            include '**/*.java'
        }
    }
}
```

### Example Pattern

- Simple classes without package declarations
- Each class has a `public static void main(String[] args)` method
- Focused on demonstrating specific Java concepts
- No external dependencies beyond standard Java library

## Development Environment

- **Java Version**: 21 (LTS) - enforced by Gradle toolchain
- **Build Tool**: Gradle 8 with wrapper
- **IDE**: IntelliJ IDEA or VS Code recommended

### VS Code Extensions

Essential extensions for Java/Gradle/Spring Boot development:

**Core Java Development:**

- `Extension Pack for Java` - Complete Java development suite
- `Language Support for Java by Red Hat` - Java language server
- `Debugger for Java` - Debugging support
- `Project Manager for Java` - Project management

**Build Tool Extensions:**

- `Gradle for Java` - Gradle support and build server
- `Maven for Java` - Maven support (if needed)

**Spring Boot Extensions:**

- `Spring Boot Extension Pack` - Complete Spring Boot suite
- `Spring Boot Tools` - Enhanced Spring Boot support
- `Spring Initializr Java Support` - Project generation

**Code Quality Extensions:**

- `Checkstyle for Java` - Checkstyle integration
- `SonarLint` - Real-time code quality analysis
- `Error Lens` - Inline error/warning display

**Utility Extensions:**

- `REST Client` - Test APIs with .http files
- `Docker` - Container development support

## Adding New Examples

When adding new Java examples:

1. Create folder under `src/`: `mkdir -p src/lesson03`
2. Create Java file: `src/lesson03/YourExample.java`
3. Use simple class structure (no package declaration needed)
4. Add `public static void main(String[] args)` method
5. Run with: `./gradlew runSimple -Pexample=lesson03/YourExample`

## CI/CD Pipeline

The GitHub Actions workflow runs:

1. **Compilation**: `./gradlew compileJava`
2. **Tests**: `./gradlew test`
3. **Linting**: `./gradlew lint` (Google Java Style + PMD + SpotBugs)
4. **Full Validation**: `./gradlew preCommit`

All checks must pass for CI to succeed.

## Project Purpose

This is an educational repository for learning Java fundamentals. The structure prioritizes simplicity and ease of running individual examples over enterprise Java patterns, while maintaining professional code quality standards through automated linting and validation.