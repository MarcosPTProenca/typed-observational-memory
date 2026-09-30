---
name: java-docs
description: 'Ensure that Java types are documented with Javadoc comments and follow best practices for documentation.'
---

# Java Documentation (Javadoc) Best Practices

- Public and protected members should be documented with Javadoc comments.
- It is encouraged to document package-private and private members as well, especially if they are complex or not self-explanatory.
- The first sentence of the Javadoc comment is the summary description. It should be a concise overview of what the method does and end with a period.
- Use `<REDACTED_USER>` for method parameters. The description starts with a lowercase letter and does not end with a period.
- Use `<REDACTED_USER>` for method return values.
- Use `<REDACTED_USER>` or `<REDACTED_USER>` to document exceptions thrown by methods.
- Use `<REDACTED_USER>` for references to other types or members.
- Use `{<REDACTED_USER>}` to inherit documentation from base classes or interfaces.
  - Unless there is major behavior change, in which case you should document the differences.
- Use `<REDACTED_USER> <T>` for type parameters in generic types or methods.
- Use `{<REDACTED_USER>}` for inline code snippets.
- Use `<pre>{<REDACTED_USER> ... }</pre>` for code blocks.
- Use `<REDACTED_USER>` to indicate when the feature was introduced (e.g., version number).
- Use `<REDACTED_USER>` to specify the version of the member.
- Use `<REDACTED_USER>` to specify the author of the code.
- Use `<REDACTED_USER>` to mark a member as deprecated and provide an alternative.