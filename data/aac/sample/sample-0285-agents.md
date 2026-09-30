# AGENTS.md

This file provides context for AI coding agents working in this repository.

## Quick Reference

| Task | Command |
|------|---------|
| Restore | `dotnet restore` |
| Build | `dotnet build` |
| Test | `dotnet test` |
| Format | `dotnet format` |
| Format check | `dotnet format --verify-no-changes` |
| Run (stdio) | `dotnet run` |
| Run (HTTP) | `dotnet run -- --http` |
| Publish | `dotnet publish -c Release` |

## Project Overview

**MCP C# Starter** is a feature-complete Model Context Protocol (MCP) server template in C# using the official csharp-sdk. It demonstrates all major MCP features including tools, resources, resource templates, prompts, sampling, progress updates, and dynamic tool loading.

**Purpose**: Workshop starter template for learning MCP server development.

## Technology Stack

- **Runtime**: .NET 8.0
- **MCP SDK**: `ModelContextProtocol` NuGet package (0.5.0-preview.1)
- **DI Framework**: Microsoft.Extensions.Hosting
- **Pattern**: Attribute-based (`[McpServerTool]`, `[McpServerResource]`, `[McpServerPrompt]`)
- **Formatter**: dotnet format (built-in)

## Project Structure

```
.
├── McpCSharpStarter.csproj     # Project file
├── global.json                  # SDK version pinning
├── appsettings.json             # Configuration
├── Program.cs                   # Main entry point (stdio/HTTP)
├── Tools/
│   └── AllTools.cs              # All tool implementations
├── Resources/
│   └── AllResources.cs          # All resource implementations
├── Prompts/
│   └── AllPrompts.cs            # All prompt implementations
├── .vscode/
│   ├── mcp.json                 # MCP server configuration
│   ├── tasks.json               # Build/run tasks
│   ├── launch.json              # Debug configurations
│   └── extensions.json
└── .devcontainer/
    └── devcontainer.json
```

## Build & Run Commands

```bash
# Restore packages
dotnet restore

# Build
dotnet build

# Run server (stdio transport - default)
dotnet run

# Run server (HTTP transport)
dotnet run -- --http
# With custom port:
dotnet run -- --http --port 8080

# Build release
dotnet publish -c Release
```

## Linting & Formatting

```bash
# Format code (required before commit)
dotnet format

# Check formatting (CI mode)
dotnet format --verify-no-changes

# Build with code style enforcement
dotnet build --warnaserror
```

## Testing

```bash
dotnet test
```

## Key Files to Modify

- **Add/modify tools**: `Tools/AllTools.cs` → Add methods with `[McpServerTool]` attribute
- **Add/modify resources**: `Resources/AllResources.cs` → Add methods with `[McpServerResource]` attribute
- **Add/modify prompts**: `Prompts/AllPrompts.cs` → Add methods with `[McpServerPrompt]` attribute
- **Server configuration**: `Program.cs`
- **HTTP port/config**: `Program.cs` → command line args

## MCP Features Implemented

| Feature | Location | Description |
|---------|----------|-------------|
| `hello` tool | `AllTools.cs` | Basic tool with annotations |
| `get_weather` tool | `AllTools.cs` | Structured JSON output |
| `ask_llm` tool | `AllTools.cs` | Sampling/LLM invocation |
| `long_task` tool | `AllTools.cs` | Progress updates |
| `load_bonus_tool` | `AllTools.cs` | Dynamic tool loading |
| Resources | `AllResources.cs` | Static `info://about`, `file://example.md` |
| Templates | `AllResources.cs` | `greeting://{name}`, `data://items/{id}` |
| Prompts | `AllPrompts.cs` | `greet`, `code_review` with arguments |

## Environment Variables / CLI Args

- `--http` - Enable HTTP transport
- `--port <port>` - HTTP server port (default: 3000)

## Conventions

- Use attribute-based MCP definitions (`[McpServerTool]`, etc.)
- Use `[Description]` attribute for parameter documentation
- Organize by feature type (Tools/, Resources/, Prompts/)
- Use .NET dependency injection patterns
- Run `dotnet format` before committing

## Code Quality Tools

- **dotnet format**: Code formatting (built-in)
- **.editorconfig**: Style configuration (if present)
- **Roslyn analyzers**: Code analysis during build

## Tool Pattern

```csharp
[McpServerToolType]
public class MyTools
{
    [McpServerTool(Name = "my_tool", Title = "My Tool")]
    [Description("Tool description")]
    public static string MyTool(
        [Description("Parameter description")] string param)
    {
        return $"Result: {param}";
    }
}
```

## Documentation Links

- [MCP Specification](https://modelcontextprotocol.io/)
- [C# SDK](https://github.com/modelcontextprotocol/csharp-sdk)
- [Building Servers](https://modelcontextprotocol.io/docs/develop/build-server)