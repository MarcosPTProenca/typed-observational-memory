# Repository Guidelines

## Project Structure & Module Organization
- `src/Core`: Core layers
  - `Domain`: entities, value objects, domain events
  - `Application`: CQRS (MediatR), validators, pipeline behaviors
  - `Infrastructure`: EF Core, external services (Binance), policies
- `src/Presentation/API`: ASP.NET Core Minimal API entry (`Program.cs`)
- `tests/Unit`, `tests/Integration`: xUnit test projects
- `docs`, `scripts`, `Dockerfile`, `docker-compose*.yml`

## Build, Test, and Development Commands
- `dotnet restore && dotnet build` — restore and build all projects
- `dotnet run --project src/Presentation/API/CryptoBot.Api.csproj` — run API (dev)
- `dotnet test --collect:"XPlat Code Coverage"` — run unit/integration tests with coverage
- `docker compose -f docker-compose.yml -f docker-compose.override.yml up -d` — run dev stack (API on `http://localhost:5000`)
- `./scripts/deploy.sh dev up` or `./scripts/deploy.ps1 dev up` — helper script for compose lifecycle

## Coding Style & Naming Conventions
- C# 12 / .NET 9 (`Nullable` + `ImplicitUsings` enabled in `Directory.Build.props`)
- Indentation: 4 spaces; prefer file-scoped namespaces
- Naming: PascalCase for types/methods; camelCase for locals/params; `_camelCase` for private fields; interfaces prefixed with `I`
- Keep layers clean: Presentation → Application → Domain; Infrastructure implements interfaces from Application

## Testing Guidelines
- Frameworks: xUnit, FluentAssertions, NSubstitute; integration uses `Microsoft.AspNetCore.Mvc.Testing` and Testcontainers (PostgreSQL)
- Structure: place tests under `tests/Unit` or `tests/Integration`; name files `ThingNameTests.cs`
- Naming: `Should_DoX_WhenY()` for clarity
- Run locally with `dotnet test`; integration tests may start containers automatically; API uses relaxed JWT in `Testing` environment

## Commit & Pull Request Guidelines
- Commits: imperative, concise subject (e.g., `Fix build errors in infrastructure services`); group related changes
- PRs: include description, rationale, screenshots/logs where relevant, and linked issues; note breaking changes and config impacts
- Checks: ensure `dotnet build` and `dotnet test` pass; run API locally or via compose to smoke test endpoints (`/health`, `/api/v1/ping`)

## Security & Configuration Tips
- Local dev and production both use PostgreSQL via `ConnectionStrings__DefaultConnection`
- Configure JWT via `Jwt__Key`, `Jwt__Issuer`, `Jwt__Audience`; never commit secrets—use environment variables or `.env`
- Binance settings: `Binance__BaseUrl`, `Binance__IsTestnet`; prefer testnet in development