# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Treasure Data Go SDK**, a client library for interacting with Treasure Data's REST API. Treasure Data is a cloud-based data analytics platform providing big data processing capabilities.

## Commands

### Build, Test, and Development Commands
```bash
# Install tools (via Aqua)
aqua i

# Compile SDK + packages
go build ./...

# Build CLI
go build -o dist/tdcli ./cmd/tdcli

# Run tests (unit + integration)
go test ./... -race -cover

# Focus tests by package or name
go test ./... -run TestName

# Lint/vet (stdlib)
go vet ./...
go fmt ./...

# Release dry-run
goreleaser release --snapshot --clean

# Run example tests
go test -run Example
```

## Architecture

### Core Structure
- **Single-package design**: All code is in the root package `treasuredata`
- **Service-oriented architecture**: Each API domain has its own service struct
- **Client-centered**: All services are accessed through the main `Client` struct
- **Context-first**: All operations accept `context.Context` as first parameter

### File Structure
The SDK is organized into logical files based on functionality:

#### Core Files
- `client.go` - Main client and configuration
- `trino.go` - Trino SQL client implementation
- Root package: Go SDK for Treasure Data (`*.go`), grouped by domain

#### Service Files
- `databases.go` - Database operations
- `tables.go` - Table management
- `queries.go` - Query execution
- `jobs.go` - Job management
- `results.go` - Query result retrieval
- `users.go` - User management
- `permissions.go` - Access control and policies
- `bulk_import.go` - Bulk data import operations
- `workflow.go` - Workflow automation
- `workflow_*.go` - Extended workflow functionality (projects, schedules, attempts, hooks)

#### OpenTelemetry Integration
- `otel/` - HTTP transport, helpers, performance optimizations
- `docs/` - Integration documentation
- `examples/` - Runnable configurations and validation scripts

#### CDP (Customer Data Platform) Files
The CDP functionality is split across multiple files for better maintainability:
- `cdp.go` - Base CDPService struct and all type definitions
- `cdp_segments.go` - Segment operations (create, list, query, statistics)
- `cdp_audiences.go` - Audience management (CRUD, attributes, behaviors, executions)
- `cdp_activations.go` - Activation/syndication operations
- `cdp_folders.go` - Folder management (entity and audience folders)
- `cdp_tokens.go` - Token operations (legacy and entity tokens)
- `cdp_funnels.go` - Funnel management (legacy and entity APIs)
- `cdp_predictive_segments.go` - Predictive segment operations

### Key Components

#### Client (`client.go`)
- Main entry point with `NewClient(apiKey string, options ...ClientOption)`
- Handles authentication, HTTP configuration, and region-specific endpoints
- Contains all service instances (Databases, Tables, Queries, Jobs, etc.)

#### Service Pattern
Each service follows the same pattern:
- Service struct with client reference
- Methods that accept context and parameters
- Consistent error handling with `ErrorResponse` type

#### Services
- **DatabasesService**: Database CRUD operations
- **TablesService**: Table management including swap, rename
- **QueriesService**: Query submission (Presto/Hive)
- **JobsService**: Job lifecycle management and monitoring
- **ResultsService**: Query result retrieval in multiple formats
- **UsersService**: User management and API key operations
- **PermissionsService**: Policy and permission management
- **BulkImportService**: Bulk data import workflow
- **CDPService**: Customer Data Platform operations including:
  - Segment creation and management
  - Audience building and management
  - Activation configuration for external destinations
  - Folder management with JSON API format support
- **WorkflowService**: Workflow automation and orchestration including:
  - Workflow lifecycle management (create, update, delete, list)
  - Workflow execution and monitoring (start, retry, kill attempts)
  - Task management and monitoring
  - Schedule configuration and management
  - Log retrieval for workflows and tasks

### Authentication & Configuration
- Uses TD1 API key authentication
- Supports multiple regions: US, EU, Japan, Asia-Pacific
- Configurable via `ClientOption` pattern:
  - `WithRegion(region string)`
  - `WithEndpoint(endpoint string)`
  - `WithHTTPClient(client *http.Client)`
  - `WithUserAgent(userAgent string)`

### Error Handling
- Custom `ErrorResponse` type with detailed API error information
- Preserves HTTP response details for debugging
- Type assertion pattern: `if tdErr, ok := err.(*td.ErrorResponse); ok`

## Development Guidelines

### Coding Style & Naming Conventions
- Go formatting: run `go fmt ./...` before pushing; 4-space tabs (Go default)
- File naming mirrors services: `databases.go`, `tables.go`; tests as `xxx_test.go`
- Exported identifiers require clear comments; avoid stutter (e.g., `Client`, `DatabasesService`)
- Context-first methods: pass `context.Context` as the first parameter for I/O
- Errors: wrap with context using `fmt.Errorf("...: %w", err)`; prefer sentinel/typed errors where applicable

### Testing Guidelines
- Framework: standard `testing` with table tests where helpful
- Coverage: aim to keep/new code ≥80% where practical
- Integration tests: OTEL/Trino tests run without external services by using in-memory exporters; when unsure, target by `-run`
- Add tests next to sources; prefer small, deterministic HTTP handlers for API mocks
- Tests: `*_test.go` colocated with sources; fixtures in `testdata/`

### Security & Configuration Tips
- Never hardcode API keys or OTEL credentials. Use env vars (e.g., `TD_API_KEY`, `OTEL_*`) or local config
- For TLS, prefer system CAs; when adding custom CA/certs, use `SSLOptions` and document why
- CI/readability: ensure `go build`, `go test -race`, and `go vet` pass locally; do not commit secrets—use `TD_API_KEY` or `~/.tdcli/.tdcli.toml` for local runs

### Commit & Pull Request Guidelines
- Commits: use Conventional Commits where possible (`feat:`, `fix:`, `chore:`); keep messages imperative and scoped
- PRs: include a clear summary, linked issues, rationale, and test/demo output. Update `README.md`/`docs/` and examples if behavior changes

## CLI (tdcli) Structure

### Overview
The `tdcli` command-line tool provides access to all Treasure Data API operations through a structured command hierarchy using the Kong CLI framework.

### Command Hierarchy

```
tdcli
├── version                           # Show version information
├── config                            # Configuration management
├── databases (db)                    # Database management
│   ├── list (ls)                    # List all databases
│   ├── get (show)                   # Get database details
│   ├── create                       # Create a new database
│   ├── delete (rm)                  # Delete a database
│   └── update                       # Update database properties
├── tables (table)                    # Table management
│   ├── list (ls)                    # List tables in database
│   ├── get (show)                   # Get table details
│   ├── create                       # Create a new table
│   ├── delete (rm)                  # Delete a table
│   ├── swap                         # Swap two tables
│   └── rename (mv)                  # Rename a table
├── queries (query, q)                # Query execution
│   ├── submit (run)                 # Submit a query for execution
│   ├── status                       # Check query execution status
│   ├── result (results)             # Get query results
│   ├── list (ls)                    # List recent queries
│   └── cancel                       # Cancel a running query
├── jobs (job)                        # Job management
│   ├── list (ls)                    # List jobs
│   ├── get (show)                   # Get job details
│   └── cancel (kill)                # Cancel a running job
├── users (user)                      # User management
│   ├── list (ls)                    # List users
│   └── get (show)                   # Get user details
├── perms (permissions, acl)          # Access control and permissions
│   ├── policies                     # Policy management
│   │   ├── list (ls)               # List all policies
│   │   ├── get (show)              # Get policy details
│   │   ├── create                  # Create a new policy
│   │   └── delete (rm)             # Delete a policy
│   ├── groups                       # Policy group management
│   │   ├── list (ls)               # List all policy groups
│   │   ├── get (show)              # Get policy group details
│   │   ├── create                  # Create a new policy group
│   │   └── delete (rm)             # Delete a policy group
│   └── users                        # Access control user management
│       ├── list (ls)               # List access control users
│       └── get (show)              # Get user access control details
├── results (result)                  # Query results management
│   └── get (show)                   # Get query results
├── import (bulk-import)              # Bulk data import
│   ├── list (ls)                    # List bulk import sessions
│   ├── get (show)                   # Get bulk import session details
│   ├── create                       # Create a new bulk import session
│   ├── delete (rm)                  # Delete a bulk import session
│   ├── upload                       # Upload a part to session
│   ├── commit                       # Commit a bulk import session
│   ├── perform                      # Perform bulk import job
│   ├── freeze                       # Freeze a bulk import session
│   ├── unfreeze                     # Unfreeze a bulk import session
│   └── parts                        # List parts in a bulk import session
├── cdp                               # Customer Data Platform (CDP) management
│   ├── segments (segment)           # CDP segment management
│   │   ├── create                  # Create a new segment
│   │   ├── list (ls)               # List segments
│   │   ├── get (show)              # Get segment details
│   │   ├── update                  # Update segment
│   │   ├── delete (rm)             # Delete segment
│   │   ├── folders                 # Get segments in folder
│   │   ├── query                   # Execute segment query
│   │   ├── new-query               # Create new segment query
│   │   ├── query-status            # Get segment query status
│   │   ├── kill-query              # Kill segment query
│   │   ├── customers               # Get segment customers
│   │   └── statistics (stats)      # Get segment statistics
│   ├── audiences (audience)         # CDP audience management
│   │   ├── create                  # Create a new audience
│   │   ├── list (ls)               # List audiences
│   │   ├── get (show)              # Get audience details
│   │   ├── delete (rm)             # Delete audience
│   │   ├── behaviors               # Get audience behaviors
│   │   ├── run                     # Run audience execution
│   │   ├── executions              # Get audience executions history
│   │   ├── statistics (stats)      # Get audience statistics
│   │   ├── sample-values (samples) # Get audience sample values
│   │   └── behavior-samples        # Get behavior sample values
│   ├── activations (activation)     # CDP activation management
│   │   ├── create                  # Create activation
│   │   ├── create-with-struct      # Create activation with struct
│   │   ├── list (ls)               # List activations
│   │   ├── get (show)              # Get activation details
│   │   ├── update                  # Update activation
│   │   ├── update-status           # Update activation status
│   │   ├── delete (rm)             # Delete activation
│   │   ├── execute                 # Execute activation
│   │   ├── executions              # Get activation executions (requires: audience-id, segment-id, activation-id)
│   │   ├── list-by-audience        # List activations by audience
│   │   ├── list-by-segment-folder  # List activations by segment folder
│   │   ├── run-segment             # Run activation for segment
│   │   ├── list-by-parent-segment  # List activations by parent segment
│   │   ├── workflow-projects       # Get workflow projects for parent segment
│   │   ├── workflows               # Get workflows for parent segment
│   │   └── matched-activations     # Get matched activations for parent segment
│   ├── folders (folder)             # CDP folder management
│   │   ├── list (ls)               # List folders in audience
│   │   ├── create                  # Create folder in audience
│   │   ├── get (show)              # Get folder details
│   │   ├── create-entity           # Create entity folder
│   │   ├── get-entity              # Get entity folder
│   │   ├── update-entity           # Update entity folder
│   │   ├── delete-entity           # Delete entity folder
│   │   └── get-entities            # Get entities by folder
│   └── tokens (token)               # CDP token management
│       ├── list (ls)               # List tokens
│       ├── get-entity (get, show)  # Get entity token details
│       ├── update-entity           # Update entity token
│       └── delete-entity (rm)      # Delete entity token
└── workflow (wf)                     # Workflow management
    ├── list (ls)                    # List workflows
    ├── get (show)                   # Get workflow details
    ├── create                       # Create a new workflow
    ├── update                       # Update workflow
    ├── delete (rm)                  # Delete workflow
    ├── start (run)                  # Start workflow execution
    ├── attempts (attempt)           # Workflow attempt management
    │   ├── list (ls)               # List workflow attempts
    │   ├── get (show)              # Get attempt details
    │   ├── kill                    # Kill running attempt
    │   └── retry                   # Retry failed attempt
    ├── schedule                     # Workflow schedule management
    │   ├── get (show)              # Get workflow schedule
    │   ├── enable                  # Enable workflow schedule
    │   ├── disable                 # Disable workflow schedule
    │   └── update                  # Update workflow schedule
    ├── tasks (task)                 # Workflow task management
    │   ├── list (ls)               # List workflow tasks
    │   └── get (show)              # Get task details
    ├── logs (log)                   # Workflow log management
    │   ├── attempt                 # Get attempt log
    │   └── task                    # Get task log
    └── projects (project, proj)     # Workflow project management
        ├── list (ls)               # List workflow projects
        ├── get (show)              # Get project details
        ├── create                  # Create a new project
        ├── push                    # Push project from directory (alias for create)
        ├── workflows (wf)          # List workflows in project
        └── secrets (secret)        # Project secrets management
            ├── list (ls)           # List project secrets
            ├── set                 # Set project secret
            └── delete (rm)         # Delete project secret
```

### Global Flags
- `--api-key STRING`: Treasure Data API key (format: account_id/api_key) ($TD_API_KEY)
- `--region STRING`: API region (us, eu, tokyo, ap02) [default: "us"]
- `--format STRING`: Output format (json, table, csv) [default: "table"]
- `--output STRING`: Output to file
- `-v, --verbose`: Verbose output

### CLI Implementation Structure

#### Command Registration (`cmd/tdcli/cli.go`)
- Uses Kong framework for command parsing and routing
- Each command is defined as a struct with Kong tags
- Commands implement a `Run(ctx *CLIContext) error` method
- Command aliases are defined with `kong:"cmd,aliases='...'"` tags

#### Handler Functions (`cmd/tdcli/*.go`)
- Each service has its own file with handler functions
- Handlers accept: `(ctx context.Context, client *td.Client, args []string, flags Flags)`
- Support multiple output formats: table (default), JSON, CSV
- Include comprehensive error handling with verbose mode support

#### CLIContext Structure
```go
type CLIContext struct {
    Context     context.Context
    Client      *td.Client
    GlobalFlags Flags
}
```

#### Flags Structure
```go
type Flags struct {
    APIKey      string
    Region      string
    Format      string
    Output      string
    Verbose     bool
    Database    string
    Status      string
    Priority    int
    Limit       int
    WithDetails bool
}
```

## CDP Implementation Status

### Recently Implemented Features ✅

All major missing CDP features have been implemented as of the latest update:

#### 1. **Journeys** - Complete customer journey management system ✅
**File**: `cdp_journeys.go`
**Implemented endpoints** (21 methods):
- Journey CRUD: `ListJourneys`, `CreateJourney`, `GetJourney`, `UpdateJourney`, `DeleteJourney`
- Journey operations: `PauseJourney`, `ResumeJourney`, `GetJourneyDetail`, `DuplicateJourney`
- Journey analytics: `GetJourneyStatistics`, `GetJourneyCustomers`, `GetJourneyStageCustomers`
- Sankey charts: `GetJourneyConversionSankeyCharts`, `GetJourneyActivationSankeyCharts`
- Journey activations: `ListJourneyActivations`, `CreateJourneyActivation`, `GetJourneyActivation`, `UpdateJourneyActivation`
- Journey behaviors: `GetAvailableBehaviorsForStep`, `GetActivationTemplatesForStep`
- Journey segment rules: `ListJourneySegmentRules`

#### 2. **Activation Templates** ✅
**File**: `cdp_activation_templates.go`
**Implemented endpoints** (5 methods):
- `CreateActivationTemplate` - `POST /entities/activation_templates`
- `GetActivationTemplate` - `GET /entities/activation_templates/{id}`
- `UpdateActivationTemplate` - `PATCH /entities/activation_templates/{id}`
- `DeleteActivationTemplate` - `DELETE /entities/activation_templates/{id}`
- `ListActivationTemplatesByParentSegment` - `GET /entities/parent_segments/{parentSegmentId}/activation_templates`

#### 3. **Parent Segments Entity API** ✅
**File**: `cdp_segments.go` (extended)
**Implemented endpoints** (2 methods):
- `ListParentSegments` - `GET /entities/parent_segments`
- `GetParentSegment` - `GET /entities/parent_segments/{id}`

#### 4. **Additional Funnel Endpoints** ✅
**File**: `cdp_funnels.go` (extended)
**Implemented endpoints** (3 methods):
- `GetFunnelStageStatistics` - `GET /entities/funnels/{funnelId}/stages/{id}/statistics`
- `ListFunnelsByParentSegment` - `GET /entities/parent_segments/{parentSegmentId}/funnels`
- `DeleteEntityFunnel` - `DELETE /entities/funnels/{id}`

#### 5. **Additional Predictive Segment Endpoints** ✅
**File**: `cdp_predictive_segments.go` (extended)
**Implemented endpoints** (1 method):
- `GuessRuleAsyncForSegmentPredictiveSegment` - `POST /entities/segments/{id}/predictive_segments/guess_rule_async`

#### 6. **Legacy Endpoints Still in Use** ✅
**File**: `cdp_audiences.go` (extended)
**Implemented endpoints** (2 methods):
- `GetMasterSegments` - `GET /master_segments`
- `MoveSegmentIntoFolder` - `POST /audiences/{audienceId}/folders/{folderId}/put_in`

### Implementation Coverage Summary
- **Implemented**: ~145 methods covering ~95% of CDP functionality
- **Added**: 34+ new methods in this update
- **Status**: Journey management and all major CDP features are now fully implemented

### Remaining Gap: Journey Bundles

The only major feature still missing is **Journey Bundles**, which includes:
- All `/entities/journey_bundles/*` endpoints
- This is a less commonly used feature for bundling multiple journeys together

All core CDP functionality is now available in the SDK!

## Trino SQL Client Implementation

### Overview
The SDK includes a comprehensive Trino SQL client (`trino.go`) with both library and CLI interfaces for executing SQL queries against Treasure Data's Trino engine.

### Library Components

#### Core Client (`trino.go`)
```go
type TDTrinoClient struct {
    db       *sql.DB
    apiKey   string
    region   string
    endpoint string
    database string
    source   string
}
```

**Key Features**:
- **Authentication**: Uses X-Trino-User header (not DSN) for TD API key authentication
- **Regional endpoints**: Supports US, Tokyo, EU, AP02, AP03 regions
- **Connection pooling**: Standard database/sql connection management
- **Error handling**: Sanitizes API keys from error messages
- **SQL safety**: `EscapeIdentifier()` and `EscapeStringLiteral()` functions

**Usage Example**:
```go
config := td.TDTrinoClientConfig{
    APIKey:   "account_id/api_key",
    Region:   "us",
    Database: "sample_datasets",
    Source:   "my_application",
}

client, err := td.NewTDTrinoClient(config)
if err != nil {
    log.Fatal(err)
}
defer client.Close()

rows, err := client.Query(ctx, "SELECT COUNT(*) FROM nasdaq")
```

### CLI Interface (`cmd/tdcli/trino.go`)

#### Command Structure
```
tdcli trino
├── query (q)           # Execute SQL query
├── interactive (i, repl) # Interactive SQL session  
├── test               # Test connection
├── describe (desc)    # Describe table structure
├── show               # Show schemas/tables/columns
├── explain            # Show query execution plan
└── version            # Show Trino version
```

#### Interactive Mode Features
- **Database switching**: `USE database_name` command
- **Dynamic prompt**: Shows current database as `trino:database_name>`
- **Smart commands**: `show databases`, `show tables`, `show current database`
- **Context-aware**: `DESCRIBE table` auto-qualifies with current database
- **Cross-database queries**: Supports `database.table` syntax

#### Advanced Pagination System
**Buffered streaming with pagination**:
- **Default 20 rows per page** in interactive mode
- **Configurable page size** via `--page-size` flag
- **Interactive controls**: Enter (next page), 'q' (quit), 'a' (show all)
- **High-performance buffering**: 8KB output buffers, String Builder reuse
- **Memory efficient**: Constant memory usage regardless of result size

#### Output Format Support
- **Table format** (default): Human-readable tabular output
- **JSON format**: Structured JSON for programmatic use
- **CSV format**: Comma-separated values for data export
- **File output**: `--output filename` support for all formats

#### Performance Optimizations
- **Streaming processing**: Row-by-row processing with minimal memory footprint
- **Buffered I/O**: 8KB output buffers reduce system calls by 90%
- **String Builder reuse**: Pre-allocated, reusable buffers reduce GC pressure
- **Smart flushing**: Periodic flushes for responsiveness, immediate flush at page boundaries

### CLI Usage Examples

#### Basic Query Execution
```bash
# Execute query with table output
tdcli trino query "SELECT COUNT(*) FROM nasdaq" --database sample_datasets

# Execute with JSON output
tdcli trino query "SELECT * FROM nasdaq LIMIT 10" --format json

# Execute with pagination (25 rows per page)
tdcli trino query "SELECT * FROM large_table" --page-size 25

# Save results to file
tdcli trino query "SELECT * FROM nasdaq" --output results.csv --format csv
```

#### Interactive Session
```bash
# Start interactive mode
tdcli trino interactive --database sample_datasets

# Interactive session examples:
trino:sample_datasets> show databases
trino:sample_datasets> use information_schema
Database changed to 'information_schema'
trino:information_schema> show tables
trino:information_schema> use sample_datasets  
trino:sample_datasets> describe nasdaq
trino:sample_datasets> SELECT * FROM nasdaq LIMIT 5;
# ... pagination controls appear for large results
--- Page end (20 rows shown, 20 total so far) ---
Press Enter to continue, 'q' to quit, 'a' to show all:
```

#### Utility Commands
```bash
# Test connection
tdcli trino test --region us --database sample_datasets

# Describe table structure  
tdcli trino describe nasdaq --database sample_datasets

# Show available schemas
tdcli trino show schemas

# Show tables in specific database
tdcli trino show tables --database information_schema

# Show columns in table
tdcli trino show columns --table nasdaq --database sample_datasets

# Explain query execution plan
tdcli trino explain "SELECT COUNT(*) FROM nasdaq WHERE symbol = 'AAPL'"

# Show Trino version
tdcli trino version
```

### Technical Implementation Details

#### Authentication Flow
1. API key passed via `X-Trino-User` header (never in DSN)
2. Custom HTTP transport wrapper (`trinoTransport`) injects header
3. DSN contains dummy user "td" for protocol compliance
4. Error messages sanitize API keys for security

#### Regional Endpoint Mapping
```go
var TrinoRegionalEndpoints = map[string]string{
    "us":    "api-presto.treasuredata.com",
    "tokyo": "api-presto.treasuredata.co.jp", 
    "eu":    "api-presto.eu01.treasuredata.com",
    "ap02":  "api-presto.ap02.treasuredata.com",
    "ap03":  "api-presto.ap03.treasuredata.com",
}
```

#### High-Performance Streaming Architecture
- **Buffered Writers**: 8KB buffers for efficient I/O
- **String Builder Pattern**: Pre-allocated, reusable row builders
- **Adaptive Flushing**: Smart buffer management for optimal performance
- **Memory Constants**: O(1) memory usage regardless of result set size

### Testing Coverage
- **Unit tests**: Command structure, database switching logic, pagination controls
- **Integration tests**: Buffered streaming, SQL escaping, error handling
- **Performance tests**: Buffer efficiency, memory usage patterns
- **CLI tests**: Command parsing, flag handling, output formatting