# AGENTS.md

This file provides build commands and code style guidelines for agents working on this Go pomodoro CLI project.

## Build, Test, and Lint Commands

### Building
```bash
# Build the project
go build -o pomodoro ./...

# Run the application
go run main.go

# Build for different platforms
GOOS=linux GOARCH=amd64 go build -o pomodoro-linux .
GOOS=darwin GOARCH=amd64 go build -o pomodoro-mac .
GOOS=windows GOARCH=amd64 go build -o pomodoro.exe .
```

### Testing
```bash
# Run all tests
go test ./...

# Run tests with verbose output
go test -v ./...

# Run a specific test file
go test -v main_test.go

# Run a specific test function
go test -v -run TestFunctionName ./...

# Run tests with coverage
go test -cover ./...

# Run tests with coverage report
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out
```

### Linting and Formatting
```bash
# Format code
go fmt ./...

# Format single file
go fmt main.go

# Run vet
go vet ./...

# Staticcheck (if installed)
staticcheck ./...

# Run golangci-lint (if installed)
golangci-lint run
```

### Dependency Management
```bash
# Tidy dependencies
go mod tidy

# Verify dependencies
go mod verify

# Download dependencies
go mod download

# Update dependencies
go get -u ./...
```

## Code Style Guidelines

### Import Organization
- Use standard Go import formatting (`go fmt` handles this)
- Group imports: standard library first, third-party second
- No blank lines between groups unless needed
- Keep imports minimal - remove unused imports

### Types and Constants
- Use PascalCase for exported types: `Timer`, `TimerConfig`, `State`, `Status`
- Use unexported (lowercase) types for internal use only
- Use iota for enum-like constants: `TimerFocus`, `TimerShortBreak`, `TimerLongBreak`
- Constants should follow the type they belong to: `TimerFocus` not `FocusTimer`
- Always define a default or "Unknown" variant as the first iota value

### Naming Conventions
- **Exported functions/types**: PascalCase (`Main`, `Timer`, `cli`)
- **Private functions/variables**: camelCase (`elapsed`, `currentTimer`)
- **Constants**: PascalCase with type prefix (`TimerFocus`, `StatusPlay`)
- **Package names**: lowercase, single word when possible (`main`, `timer`)
- **Interfaces**: Should typically be named with -er suffix (`Runner`, `Ticker`)
- **Booleans**: Use prefixes like `Is`, `Has`, `Can` for clarity

### Structs and Fields
- Struct fields are lowercase (unexported) by default
- Use exported fields only when necessary
- Initialize structs with named fields: `State{currentTimer: TimerFocus, elapsed: 0, status: StatusPlay}`
- Use pointer receivers when method needs to modify receiver: `func (s *State) Update()`
- Use value receivers when method doesn't modify: `func (t Timer) Duration()`

### Error Handling
- Check all errors: `err := ...; if err != nil { return err }`
- Use error wrapping for context: `fmt.Errorf("operation failed: %w", err)`
- Use panic only for truly unrecoverable conditions (e.g., "Unknown Timer" in switch)
- Log errors appropriately for CLI applications
- Return meaningful error messages

### Functions and Methods
- Keep functions focused and small
- Use descriptive names that describe what they do (`tick`, `cli`, `main`)
- Limit parameter count - consider structs if > 3-4 parameters
- Return errors as the last return value
- Use defer for cleanup: `defer ticker.Stop()`

### Channels and Concurrency
- When using channels, always consider how to clean them up
- Use `defer` to close channels when ownership is clear
- Use buffered channels when you need to prevent blocking: `make(chan bool, 1)`
- Be explicit about channel direction when possible: `chan<- bool`, `<-chan bool`
- Always consider goroutine lifecycle - how will it terminate?

### Comments and Documentation
- Use `//` for single-line comments
- Use `/* */` for multi-line comments (though Go prefers `//`)
- Exported types/functions should have package-level comments
- Comment non-obvious logic: `// wait on the timer to finish`
- Use TODO comments for future work with reference if applicable
- Avoid obvious comments like `// increment i`

### Code Organization
- Keep related types and functions together
- Define constants before the types that use them
- Order: package doc → imports → constants → types → functions
- Main function typically at the bottom
- Use blank lines to separate logical sections

### Package Structure
- When adding packages, keep them focused (e.g., `timer`, `config`, `ui`)
- Avoid circular dependencies
- Keep main package minimal - delegate to subpackages when appropriate
- Use subdirectories for packages when the project grows

### Specific to This Project
- This is a CLI application - focus on user experience
- Timer durations should use `time.Minute`, `time.Second` constants
- Default sequence: f/s/f/s/f/s/f/l (focus/short break, long break at end)
- Status tracking: Play/Pause/Stop states
- Use channels for timer coordination (ticker, done signals)
- Consider adding configuration file support in future versions

### Testing
- Write tests for all exported functions
- Use table-driven tests for multiple scenarios
- Test both success and error paths
- Mock time/time.Sleep in tests for deterministic behavior
- Keep tests fast - use t.Parallel() when possible