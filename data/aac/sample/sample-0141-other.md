---
name: rust
description: Rust best practices with ownership, error handling, and performance.
---

- Run `cargo fmt`, `cargo clippy -- -D warnings`, and `cargo check` before finalizing changes.
- Use `Result<T, E>`/`Option<T>` consistently; avoid `.unwrap()` and `.expect()` outside tests.
- Define domain errors with `thiserror`; propagate with `?` and preserve actionable context.
- Prefer borrowing where clear, but optimize for API ergonomics over lifetime cleverness.
- Keep allocation and cloning explicit in hot paths; benchmark before micro-optimizing.
- Separate unit tests (`#[cfg(test)]`) and integration tests (`tests/`) with meaningful coverage.
- Use newtypes/enums for domain safety instead of primitive obsession.
- Gate unsafe code with documented invariants and minimal scope.