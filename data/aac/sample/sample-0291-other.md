---
name: java-junit
description: 'Get best practices for JUnit 5 unit testing, including data-driven tests'
---

# JUnit 5+ Best Practices

Your goal is to help me write effective unit tests with JUnit 5, covering both standard and data-driven testing approaches.

## Project Setup

- Use a standard Maven or Gradle project structure.
- Place test source code in `src/test/java`.
- Include dependencies for `junit-jupiter-api`, `junit-jupiter-engine`, and `junit-jupiter-params` for parameterized tests.
- Use build tool commands to run tests: `mvn test` or `gradle test`.

## Test Structure

- Test classes should have a `Test` suffix, e.g., `CalculatorTest` for a `Calculator` class.
- Use `<REDACTED_USER>` for test methods.
- Follow the Arrange-Act-Assert (AAA) pattern.
- Name tests using a descriptive convention, like `methodName_should_expectedBehavior_when_scenario`.
- Use `<REDACTED_USER>` and `<REDACTED_USER>` for per-test setup and teardown.
- Use `<REDACTED_USER>` and `<REDACTED_USER>` for per-class setup and teardown (must be static methods).
- Use `<REDACTED_USER>` to provide a human-readable name for test classes and methods.

## Standard Tests

- Keep tests focused on a single behavior.
- Avoid testing multiple conditions in one test method.
- Make tests independent and idempotent (can run in any order).
- Avoid test interdependencies.

## Data-Driven (Parameterized) Tests

- Use `<REDACTED_USER>` to mark a method as a parameterized test.
- Use `<REDACTED_USER>` for simple literal values (strings, ints, etc.).
- Use `<REDACTED_USER>` to refer to a factory method that provides test arguments as a `Stream`, `Collection`, etc.
- Use `<REDACTED_USER>` for inline comma-separated values.
- Use `<REDACTED_USER>` to use a CSV file from the classpath.
- Use `<REDACTED_USER>` to use enum constants.

## Assertions

- Use the static methods from `org.junit.jupiter.api.Assertions` (e.g., `assertEquals`, `assertTrue`, `assertNotNull`).
- For more fluent and readable assertions, consider using a library like AssertJ (`assertThat(...).is...`).
- Use `assertThrows` or `assertDoesNotThrow` to test for exceptions.
- Group related assertions with `assertAll` to ensure all assertions are checked before the test fails.
- Use descriptive messages in assertions to provide clarity on failure.

## Mocking and Isolation

- Use a mocking framework like Mockito to create mock objects for dependencies.
- Use `<REDACTED_USER>` and `<REDACTED_USER>` annotations from Mockito to simplify mock creation and injection.
- Use interfaces to facilitate mocking.

## Test Organization

- Group tests by feature or component using packages.
- Use `<REDACTED_USER>` to categorize tests (e.g., `<REDACTED_USER>("fast")`, `<REDACTED_USER>("integration")`).
- Use `<REDACTED_USER>(MethodOrderer.OrderAnnotation.class)` and `<REDACTED_USER>` to control test execution order when strictly necessary.
- Use `<REDACTED_USER>` to temporarily skip a test method or class, providing a reason.
- Use `<REDACTED_USER>` to group tests in a nested inner class for better organization and structure.