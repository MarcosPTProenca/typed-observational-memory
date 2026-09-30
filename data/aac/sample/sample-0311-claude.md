# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is the MVP for a full-stack budget tracking application with:
- **Backend**: ASP.NET Core 10 Web API with minimal APIs and Entity Framework Core
- **Frontend**: React 18 with TypeScript, Vite, and Tailwind CSS
- **Database**: PostgreSQL 17
- **Infrastructure**: Docker Compose for local development

**Important:** this project is used as a demo. Prefer simple, readable and composable code.

### Core Components

**API Structure (src/BudgetTracker.Api/)**:
- Feature-based organization with `Auth/` and `AntiForgery/` folders
- Uses minimal APIs in `Program.cs` rather than traditional controllers
- Implements multiple authentication schemes: Identity cookies + Static API keys

**Frontend Structure (src/BudgetTracker.Web/)**:
- React Router v7 for routing
- TypeScript strict mode enabled
- Tailwind CSS for styling with Vite plugin
- API communication via Axios

**Key Features**:
- User authentication (registration, login, logout)
- Anti-forgery protection
- Multi-tenant support with user isolation
- CSV transaction import with auto-detection of bank formats
- AI-powered transaction categorization and recommendations
- Semantic search over transactions using vector embeddings

## C# Recommendations
- Prefer clear names over generic names like Repository, Service, Manager, etc.
- Avoid using comments to overexplain everything

## Common Development Commands

### Backend (.NET)
```bash
# Build solution
dotnet build

# Run API (from src/BudgetTracker.Api/)
dotnet run
# or with hot reload
dotnet watch run

# Run tests
dotnet test
# Run specific test with detailed output
dotnet run -p tests/BudgetTracker.Api.Tests --output detailed --filter-query "/path/to/test"

# Database migrations (from src/BudgetTracker.Api/)
dotnet ef migrations add MigrationName
dotnet ef database update
```

### Frontend (React)
```bash
# Install dependencies (from src/BudgetTracker.Web/)
npm install

# Development server
npm run dev

# Build for production
npm run build

# Lint code
npm run lint

# Preview production build
npm preview
```

### Database Setup
```bash
# Start PostgreSQL with Docker (from docker/)
docker compose up -d

# Stop database
docker compose down
```

## Testing Strategy

- Uses Microsoft Testing Platform (not VSTest)
- Uses xUnit v3
- Test naming follows snake_case convention: `Should_do_when_something`
- Integration tests use Testcontainers for isolated database testing
- Mocking with NSubstitute preferred
- No code comments - use descriptive method/class names instead

## Authentication & Security

- Dual authentication: Identity (cookie-based) + Static API keys
- Anti-forgery protection with conditional filtering
- User isolation enforced at database query level
- API keys configured via `StaticApiKeysConfiguration` section

## AI Integration

- Azure OpenAI integration for transaction insights and recommendations
- Vector search using pgvector with embeddings
- Background processing for AI-generated recommendations
- Query assistance via natural language processing

## Development Notes

- .NET 10 with nullable reference types enabled
- PostgreSQL connection: `Host=localhost;Port=5432;Database=budgettracker;Username=budgetuser;Password=budgetpass123`
- API runs on http://localhost:5295, Frontend on http://localhost:5173
- Swagger UI available at http://localhost:5295/swagger
- CORS configured for local development between ports 5295 and 5173

## Agent Recommendations

- When one of the applications is started for testing, make sure it's stopped once finished.