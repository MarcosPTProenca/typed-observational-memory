---
name: java-spring
description: Java Spring Boot conventions with dependency injection, validation, and testing.
---

- Build with `./mvnw verify` or `./gradlew build`; enforce Checkstyle + SpotBugs in CI.
- Run tests with JUnit 5 + AssertJ; mock with Mockito; use `<REDACTED_USER>` only for integration tests, `<REDACTED_USER>` / `<REDACTED_USER>` for slices.
- Use constructor injection exclusively; never `<REDACTED_USER>` on fields; declare dependencies `final`.
- Validate inputs with `<REDACTED_USER>` + Bean Validation (`<REDACTED_USER>`, `<REDACTED_USER>`); handle `MethodArgumentNotValidException` globally with `<REDACTED_USER>`.
- Scope `<REDACTED_USER>` to the service layer; default read-only for queries (`readOnly = true`); never put it on controllers.
- Use OpenAPI annotations (`<REDACTED_USER>`, `<REDACTED_USER>`) on controllers for accurate API docs; return `ResponseEntity<T>` for explicit HTTP status control.