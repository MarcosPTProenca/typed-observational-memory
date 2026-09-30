# Repository Guidelines

## Project Structure & Module Organization
- Root `pom.xml` is a Maven parent (packaging `pom`) that aggregates microservice modules.
- Modules: `ecommerce-common` (shared API envelope, exceptions, async config) plus services like `user-service`, `product-service`, `inventory-service`, `cart-service`, `order-service`, `payment-service`, and `shipping-service`.
- Each module uses standard Maven layout:
  - Code: `<module>/src/main/java`
  - Config/assets: `<module>/src/main/resources` (see `application.yml`)
  - Tests (when present): `<module>/src/test/java`
- Deployment/dev assets live at repo root: `Dockerfile` and `docker-compose.yml`.

## Build, Test, and Development Commands
Prereqs: Java 21, Maven 3.9+, Docker.

- Build all modules: `mvn clean package`
- Build one service and required deps: `mvn -pl user-service -am package`
- Run a service from source: `mvn -pl user-service spring-boot:run`
- Run a built jar: `java -jar user-service/target/user-service-0.0.1-SNAPSHOT.jar`
- Start full stack (MySQL + all services): `docker compose up --build`

## Coding Style & Naming Conventions
- Use standard Java formatting with 4‑space indentation and one public class per file.
- Packages follow `com.example.ecommerce.<service>` with subpackages such as `controller`, `entity`, `repository`, and `service`.
- Naming patterns:
  - Controllers: `UserController`, mapped under `/api/...`
  - Entities: `User`, `OrderItem`
  - Repositories: `UserRepository` (Spring Data JPA)
  - Variables/methods: `lowerCamelCase`; constants: `UPPER_SNAKE_CASE`
- Prefer Lombok (`<REDACTED_USER>`, `<REDACTED_USER>`, etc.) where already used, and reuse shared types from `ecommerce-common` (e.g., `ApiResponse`).

## Testing Guidelines
- No tests are checked in yet. Add new tests under `<module>/src/test/java`.
- Use JUnit 5 and Spring Boot testing support (`spring-boot-starter-test`) when introducing tests.
- Conventions: name unit tests `*Test` and integration tests `*IT`.
- Run tests: `mvn test` (all modules) or `mvn -pl order-service test` (single module).

## Commit & Pull Request Guidelines
- There is no commit history yet; follow Conventional Commits: `feat:`, `fix:`, `refactor:`, `docs:`. Include module scope, e.g., `feat(user-service): add address endpoints`.
- PRs should include: a clear summary, affected modules, API examples (curl/Postman) for new endpoints, and notes on schema/config changes. Ensure module tests pass before merging.

## Configuration & Security Tips
- Service config lives in each module’s `src/main/resources/application.yml`. Do not commit secrets; prefer environment variables for credentials.
- Local DB defaults come from `docker-compose.yml` (`jdbc:mysql://mysql:3306/ecommerce`, user/password `ecommerce`).