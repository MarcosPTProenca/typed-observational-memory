This project is a Kotlin Spring Boot app that uses Flyway for database migrations.

Development workflow:
- Default database: PostgreSQL. Configure connection via environment variables in `src/main/resources/application.yaml` (`DB_URL`, `DB_USERNAME`, `DB_PASSWORD`, `DB_DRIVER`, `DB_MAX_POOL_SIZE`). Flyway runs automatically on startup.
- For local development, spin up PostgreSQL with `docker-compose up -d` using the provided `docker-compose.yml`.
- Tests run against an in-memory H2 database in PostgreSQL compatibility mode. Migrations also execute during tests to validate them. Run `./gradlew test --no-daemon --console=plain`.
- Initial migration creates an `examples` table at `src/main/resources/db/migration/V1__create_examples_table.sql`.

Use Gradle wrapper commands (`./gradlew`) to build and test. No special setup is required beyond Java 21.