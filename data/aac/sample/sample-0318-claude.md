# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a cryptocurrency trading bot system being rewritten in C# 13/.NET 9 following Clean Architecture principles. The project is in early development stages with a focus on maintainability, performance, and scalability.

## Architecture

The codebase follows Clean Architecture with clear separation of concerns:

```
src/
├── Core/
│   ├── Domain/          # Entities, value objects, enums (no dependencies)
│   ├── Application/     # Use cases, CQRS/MediatR, DTOs, validators, interfaces (planned)
│   └── Infrastructure/  # EF Core, external services, implementations (planned)
├── Presentation/
│   └── API/            # ASP.NET Core Minimal API with Swagger
└── Tests/              # Unit and integration tests (planned)
```

### Key Architectural Decisions
- **Clean Architecture**: Core domain is dependency-free, dependencies flow inward
- **CQRS Pattern**: Using MediatR for command/query separation (planned)
- **Database**: PostgreSQL for all environments with local development support
- **API Style**: Minimal APIs with OpenAPI/Swagger documentation
- **Target Framework**: .NET 9.0 with C# 13 language features

## Development Commands

### Build
```bash
# Build entire solution (once solution file exists)
dotnet build

# Build specific project
dotnet build src/Presentation/API/CryptoBot.Api.csproj
```

### Run
```bash
# Run the API (from project directory)
cd src/Presentation/API
dotnet run

# Run with watch mode for development
dotnet watch run
```

### User Secrets (Development)
```bash
# Initialize user secrets for API project
cd src/Presentation/API
dotnet user-secrets init

# Set JWT key (already configured)
dotnet user-secrets set "Jwt:Key" "your-super-secret-jwt-key-that-should-be-at-least-256-bits-long-for-security"
```

### Test
```bash
# Run all tests
dotnet test

# Run integration tests only (requires Docker)
dotnet test tests/Integration/CryptoBot.IntegrationTests/

# Run unit tests only
dotnet test tests/Unit/CryptoBot.UnitTests/

# Run with coverage
dotnet test --collect:"XPlat Code Coverage"
```

### Database (PostgreSQL)
```bash
# Add migration
dotnet ef migrations add <MigrationName> -p src/Core/Infrastructure -s src/Presentation/API

# Update database
dotnet ef database update -p src/Core/Infrastructure -s src/Presentation/API

# Drop and recreate database (development only)
dotnet ef database drop -f -p src/Core/Infrastructure -s src/Presentation/API
```

### Local Development Setup
- **Database**: PostgreSQL running on localhost:5432
- **Connection**: Configured in appsettings.Development.json
- **Database Name**: cryptobot
- **User**: postgres (no password required for local development)
- **F5 Ready**: Hit F5 in Visual Studio to run with local PostgreSQL

## Project Structure Details

### Current State
- **Domain Project**: Basic setup with global usings
- **Application Project**: MediatR CQRS pattern with FluentValidation, pipeline behaviors for logging and validation
- **Infrastructure Project**: EF Core setup with PostgreSQL database provider
- **API Project**: Minimal API with CQRS endpoints, health checks, CORS, and Swagger
- **Build Properties**: Centralized configuration with nullable reference types, latest C# features

### Core Components
- **CQRS Pattern**: MediatR with validation and logging pipeline behaviors
- **Database**: EF Core with CryptoBotDbContext, PostgreSQL for all environments
- **Validation**: FluentValidation integrated into MediatR pipeline
- **API Documentation**: OpenAPI/Swagger with endpoint documentation
- **Domain Models**: Complete set of entities (TradingPair, Candle, Order, Trade, Strategy, Bot, SafetyCheck)
- **Value Objects**: Type-safe TradingPairSymbol, Price, Quantity, and Timeframe with validation
- **Application Interfaces**: Comprehensive abstractions for exchanges, indicators, trading, and bot management
- **Enums**: All necessary domain enums for order types, statuses, bot states, and safety checks
- **Binance Integration**: Complete REST API client with market data, pricing, and trading pair retrieval
- **Technical Indicators**: Full implementation with Skender.Stock.Indicators (SMA, EMA, RSI, MACD, Bollinger Bands, Stochastic, Volatility)
- **Safety Policies**: MaxDrawdownPolicy and DailyLossPolicy with configurable thresholds
- **EF Core Configurations**: Entity mappings for all domain objects with proper relationships and indexes
- **HTTP Clients**: Configured HTTP clients for external API integration

### Enterprise-Grade Enhancements
- **Central Package Management**: Directory.Packages.props for consistent versioning across all projects
- **Enhanced Observability**: Serilog structured logging, OpenTelemetry metrics/tracing, Prometheus integration
- **Advanced Caching System**: Multi-provider caching (Memory, Redis, Hybrid L1/L2) with cache-aside pattern
- **Session Management**: Redis-backed sessions with HTTP-only cookies and security policies
- **Comprehensive Configuration Management**: 
  - **Secrets Management**: Multi-provider secrets (GitHub, Environment, User Secrets) with encryption
  - **Automated Secrets Rotation**: GitHub Actions workflows for daily/weekly rotation
  - **Environment Configuration**: Environment-specific settings with validation and health monitoring
  - **Advanced Feature Flags**: User targeting, dependencies, analytics, and comprehensive management

### Development Status
**✅ Configuration Management Complete**: Enterprise-grade configuration system implemented
- **Secrets Management**: Multi-provider system with GitHub API integration and automatic encryption
- **Automated Rotation**: GitHub Actions workflows for daily JWT/DB rotation and weekly API keys
- **Environment Management**: Comprehensive environment-specific configuration with validation
- **Feature Flags**: Advanced feature flag system with user targeting and dependency management
- **Administrative APIs**: 50+ REST endpoints for complete configuration management
- **Security Implementation**: JWT-protected endpoints with comprehensive audit trails
- **Monitoring & Analytics**: Configuration health scoring, usage statistics, and compliance reporting

## API Endpoints

### Core Trading & Bot Management
- `GET /api/v1/ping` - Liveness check, returns `{ "message": "pong" }`
- `GET /health` - Health check with database connectivity, returns detailed status
- `POST /api/v1/auth/token` - JWT authentication (demo: username=demo, password=demo123)
- `GET /api/v1/market/status` - Market status query (CQRS), returns market information
- `POST /api/v1/bot/start` - Start bot command (CQRS), requires authentication
- Bot management, trading, and portfolio endpoints available

### Configuration Management (50+ Endpoints)
- **Secrets Management** (`/api/v1/secrets/*`) - Secret validation, metadata, health checks
- **Secret Rotation** (`/api/v1/rotation/*`) - Manual rotation, status monitoring, workflow triggers
- **Environment Management** (`/api/v1/environment/*`) - Environment config, health, validation
- **Feature Flags** (`/api/v1/features/*`) - Flag management, evaluation, analytics, metadata
- **Session Management** (`/api/v1/sessions/*`) - Session data management and monitoring
- **Cache Management** (`/api/v1/cache/*`) - Cache operations, monitoring, and invalidation

### Documentation & Security
- Swagger UI available at `/swagger` with JWT bearer authentication support
- All administrative endpoints require JWT authentication
- Comprehensive OpenAPI documentation with request/response schemas

## Development Guidelines

### Code Style
- Use nullable reference types (`<Nullable>enable</Nullable>`)
- Leverage implicit usings and global usings
- Follow Clean Architecture dependency rules
- Prefer minimal APIs over controllers for simplicity

### Testing Strategy
- Unit tests for domain logic and value objects
- Integration tests for API endpoints and database operations
- **Testcontainers**: PostgreSQL containerized testing with Docker
- **100% integration test pass rate**: All 24 tests passing

### Development Progress
**✅ Phase 1 Complete**: Core scaffolding and data layer
**✅ Phase 2 Complete**: Domain models, value objects, and application interfaces  
**✅ Phase 3 Complete**: Infrastructure implementations (exchanges, indicators, safety policies, EF Core)
**✅ Phase 4 Complete**: API security, versioning, authentication, and comprehensive documentation
**✅ Phase 5 Complete**: Integration testing infrastructure and database reliability

### Current Features (Phase 5 Complete)
- **API Versioning**: URL-based versioning with `/api/v1/` prefix
- **Security**: JWT Bearer authentication with user secrets configuration
- **Rate Limiting**: Fixed window policy (100 requests/minute)
- **Documentation**: Enhanced OpenAPI/Swagger with security definitions and endpoint descriptions
- **Health Checks**: Database connectivity monitoring with detailed status reporting
- **Problem Details**: Standardized error handling middleware
- **CORS**: Cross-origin resource sharing for development
- **Database Integration**: PostgreSQL with EF Core migrations and Testcontainers testing
- **Testing Coverage**: 100% integration test pass rate (24/24 tests)

### Next Implementation Steps (Phase 6)
Next priorities for the trading system:
1. Implement WebSocket market data streaming for real-time updates
2. Complete bot lifecycle management services with start/stop/monitoring
3. Add live trading services for order placement and portfolio management
4. Add comprehensive performance monitoring and alerting

## Original System Context

This is a rewrite of an existing cryptocurrency trading bot with these original components being mapped to new architecture:
- `CryptoBot.Model` → Core/Domain
- `CryptoBot.Database` → Core/Infrastructure (Data)
- `CryptoBot.ExchangeEngine` → Core/Infrastructure (Exchanges) + Application abstractions
- `CryptoBot.IndicatorEngine` → Core/Infrastructure (Indicators) + Application services
- `Api.CryptoBot` → Presentation/API