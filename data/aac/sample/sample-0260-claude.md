## Architecture

**Stack:** Spring Boot 4 + WebFlux + Kotlin Coroutines + jOOQ + R2DBC + PostgreSQL

**Layered architecture:**
- **Router** (`*Router.kt`) - Defines HTTP routes using `coRouter { }` DSL with error handlers
- **Handler** (`*Handler.kt`) - Suspended request handlers, delegates to service
- **Service** (`*Service.kt`) - Business logic, `<REDACTED_USER>` annotations, throws `NotFoundException`
- **Repository** (`*Repository.kt`) - jOOQ DSL queries, returns `Flow<T>` or `suspend` functions

**Key patterns:**
- All HTTP handlers are `suspend` functions using coroutines
- Repositories use jOOQ's `asFlow()` and `awaitFirst/awaitFirstOrNull` extensions
- Service-layer `<REDACTED_USER>` works via R2DBC connection factory proxy
- Make all external contracts openapi-generated, place them in contract subproject's resources, place client and model classes in the same package as the base package of the contract owner
- IMPORTANT: Always run `./gradlew clean test` on a root project after any changes in contract subproject
- Model mapping via extension functions (e.g., `TestTable.toResponse()`)
- Don't try to replace something by default values on errors. If you received something unexpected, log and rethrow IllegalArgumentException on incoming and IllegalStateException on outgoing
- Never use optional Kotlin types for mandatory fields
- Always prefer imports to fully qualified class names
- Always remove unused imports and resources
- All versions in `build.gradle.kts` should be variables from the root `build.gradle.kts`
- When adding new dependencies, ensure they are up to date
- Use jackson 3 for all components, avoid using jackson 2 when possible
- IMPORTANT: After changing `build.gradle.kts`, always run `./gradlew clean nativeCompile test` on that subproject
- IMPORTANT: After any changes, always run `./gradlew clean test` in a corresponding subproject
- Always consider fixing warning on build or application context startup during tests execution
- Please add comments to your code when the solution is not obvious, or you need to test several approaches

**Database Patterns:**
- Each subproject should use a separate database schema. It should be defined in subproject gradle.properties, application.yml (app and test) and <REDACTED_USER> annotation in AbstractContextTest
- Create migration file in `src/main/resources/db/migration/`
- When creating migration, think about data migration when needed
- Run `./gradlew build` - jOOQ classes regenerate automatically
- Use generated classes in repository (e.g., `TEST_TABLE`, `TestTable` POJO)
- Don't use defaults in database schema, generation of id/uuid/timestamp should be explicit and code-based
- Never use optional Kotlin types for non-nullable fields. Please don't use nullability without a strong reason

## Testing

Tests use Zonky embedded PostgreSQL with Flyway auto-migration.

### Mandatory
- If the test requires a spring context and/or database, extend AbstractContextTest to avoid launching additional spring contexts and migrations
- In spring context tests never use class-wide annotations on test classes
- In spring context tests never use mocked beans in test classes to keep spring context clean
- Instead of mocks in a spring context test, add spies to AbstractContextTest to keep spring context clean
- For AbstractContextTest child tests use <REDACTED_USER> instead of inserts for initial state (if the test is not covering inserts) and <REDACTED_USER> for checks if the test is not covering reads
- Use separate folders for repository and scenario datasets, datasets for each repository also should be in a separate folder
- Write tests for all application layers
- Never use sleep in tests

Tests are organized by layer:
- `*HandlerTest` - WebTestClient-based HTTP endpoint tests
- `*ServiceTest` - Unit tests with MockK
- `*RepositoryTest` - Integration tests with an embedded database