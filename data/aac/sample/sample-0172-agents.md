# Agent Instructions

This document provides instructions for AI coding agents working on this project.

---

## Critical Rules

### Before Considering Any Task Complete

Always run the check suite before marking a task as done:

```bash
composer check
```

This command runs all quality checks in sequence:

1. **Code formatting** (`composer format:check`) - Verifies PER-CS compliance
2. **Type check** (`composer typecheck`) - Runs PHPDoc type validation
3. **Static analysis** (`composer analyze`) - Runs PHPStan analysis
4. **Tests** (`composer test`) - Runs the PHPUnit test suite with Paratest

**All checks must pass for the code to be considered complete.**

### Version Control

Never try to commit changes yourself. The user is in charge of what gets saved and discarded.

### Iterative Development

Never implement something as just a placeholder or a method definition containing just `// TODO`, unless specifically asked to take an iterative approach.

### Documentation

- If you added or changed environment variables, document them
- If you make significant architectural changes, update `README.md` to reflect this

---

## Tech Stack

This is a PHP 8.4 library for building declarative menu structures from configuration files.

### Dependencies

**Runtime:**
- `php`: ^8.4
- `symfony/yaml`: ^8.0
- `psr/simple-cache`: ^3.0

**Development:**
- `phpunit/phpunit`: ^12.0
- `brianium/paratest`: ^7.7
- `phpstan/phpstan`: ^2.0 (level max)
- `friendsofphp/php-cs-fixer`: ^3.64
- `nsrosenqvist/phpdoc-validator`: ^1.1

---

## Code Quality

### Coding Standards

- All code must follow **PER-CS 3.0** (PER Coding Style) coding standard
- All PHP files must include `declare(strict_types=1);` at the top
- Use modern PHP 8.4+ standards with strict typing
- Prefer immutable value objects where appropriate
- Use DTOs rather than array shapes
- Use enums instead of string constants

### Project Structure

```
php-menu/
├── src/
│   ├── ActiveMatcher/           # Active state detection
│   ├── Exception/               # Custom exceptions
│   ├── Loader/                  # Configuration file loaders
│   ├── Provider/                # Menu item providers
│   ├── Context.php              # Request context (current path, extras)
│   ├── Menu.php                 # Main orchestrator class
│   ├── MenuItem.php             # Immutable menu item DTO
│   └── Walker.php               # Tree walker for HTML rendering
└── tests/
    ├── Unit/                    # Unit tests (mirror src/ structure)
    ├── Feature/                 # Integration tests
    └── fixtures/                # Test fixture files (YAML, JSON, PHP)
        └── menus/
```

### Architecture Overview

- **MenuItem**: Immutable DTO representing a menu item with URL, label, active states, children, and custom attributes
- **Context**: Holds current request path, active matcher, and extra data for providers
- **Menu**: Main class that orchestrates loading configs and resolving items through providers
- **Walker**: Tree traversal utility for rendering menus to HTML with level/depth control
- **Providers**: Resolve configuration into MenuItem objects (PageProvider handles URLs, routes, file paths)
- **Loaders**: Load configuration from files (YAML, JSON, PHP) with optional caching
- **ActiveMatchers**: Determine active/activeTrail states based on current path

### Testing Standards

- Code should be adequately covered by tests
- Use PHPUnit's own mocking functionality, **never use Mockery**
- Use **camelCase** naming for test methods, NOT snake_case
- Use modern PHPUnit attributes (`#[Test]`, `#[DataProvider]`), not the `test*` prefix
- Tests go in `tests/Unit/` for unit tests and `tests/Feature/` for integration tests
- Test fixtures (sample PHP files) go in `tests/fixtures/`

### Available Commands

| Command | Description |
|---------|-------------|
| `composer check` | Run all checks (formatting, static analysis, PHPDoc type validation, tests) |
| `composer format` | Auto-fix PHP code formatting issues |
| `composer format:check` | Check PHP formatting without making changes |
| `composer analyze` | Run PHPStan static analysis |
| `composer analyze:docs` | Run PHPDoc type validation |
| `composer test` | Run PHPUnit tests with Paratest |
| `composer test:coverage` | Run tests with HTML coverage report |

### Fixing Check Failures

| Check | Fix |
|-------|-----|
| PHP formatting errors | Run `composer format` to auto-fix |
| Static analysis errors | Review PHPStan output and fix type issues manually |
| Test failures | Debug and fix the failing tests |

---

## Development Guidelines

### Adding New Features

1. Write tests first (TDD approach recommended)
2. Implement the feature in `src/`
3. Run `composer check` to verify everything passes
4. Update documentation if needed

### File Naming Conventions

- Classes: PascalCase (e.g., `TypeComparator.php`)
- Interfaces: PascalCase with `Interface` suffix (e.g., `FormatterInterface.php`)
- Test files: Mirror source structure with `Test` suffix (e.g., `TypeComparatorTest.php`)

### Type Hints

- Always use parameter type hints
- Always use return type hints
- Use union types where appropriate (`string|int`)
- Use `?Type` for nullable parameters, `Type|null` for nullable returns
- If the native type hinting and parameter name is adequate for documentation purposes, there is no need to also define it using `<REDACTED_USER>` 