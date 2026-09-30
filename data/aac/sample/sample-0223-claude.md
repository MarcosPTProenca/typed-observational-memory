# Applied Go Programming - Project Implementation Guide

# MANDATORY INITIALIZATION CHECKLIST
When executing ANY task in this repository:
1. ✓ Read and internalize _framework/CLAUDE.md 
2. ✓ Follow AECS principles in ALL interactions
3. ✓ Engage subagents for validation on ALL artifacts
4. ✓ Verify exercises are self-contained
5. ✓ Follow all Go-specific requirements below

## AECS Framework Compliance

**Primary Directive**: Follow the Agentic Exercise Curriculum System (AECS) methodology as defined in `_framework/CLAUDE.md`. All content development must enforce Exercise Primacy, Concept Atomicity, Applied Understanding, and Progressive Complexity.

## Project Overview

This repository contains a comprehensive Go programming learning Path built using AECS methodology. The Path takes developers from Go fundamentals to production mastery through hands-on Exercise completion, where every learning interaction centers on doing rather than consuming.

## Go-Specific AECS Implementation

### Subject Context
- **Subject**: Go Programming
- **Target Audience**: Experienced developers familiar with other languages
- **Approach**: Exercise-driven mastery from fundamentals to production

### Stage Progression

The Go Programming Path follows this progression:

1. **Fundamentals** - Basic Go concepts through atomic Exercises
2. **Concurrency** - Goroutines, channels, and concurrent patterns
3. **Data Structures** - Advanced data handling and algorithms  
4. **Web Programming** - HTTP servers and web applications
5. **Database Integration** - Data persistence and management
6. **Testing & Quality** - Testing strategies and code quality
7. **Performance** - Optimization and profiling
8. **Deployment** - Containerization and deployment
9. **Monitoring** - Observability and debugging
10. **Advanced Patterns** - Complex architectural patterns
11. **Production Operations** - Production-ready systems

### Go-Specific Exercise Requirements

All Go Exercises must:

- **Compile and Run**: Use Go 1.24+ compatible code that compiles without errors
- **Produce Tangible Results**: Generate console output, files, or testable behavior
- **Follow Go Idioms**: Demonstrate idiomatic Go patterns and conventions
- **Build Incrementally**: Each Exercise uses only concepts mastered in previous Exercises
- **Single Concept Focus**: Address exactly one Go concept per Exercise

### Go-Specific Incremental Step Focus

For optimal token efficiency and cognitive focus in Go exercises:

#### Critical Context (MUST preserve):
- **Package declaration**: Always show `package main` or relevant package name
- **Import statements**: Include imports relevant to new additions
- **Function signatures**: Show `func main()` and any function being modified
- **Struct definitions**: Include struct types when adding methods or fields
- **Interface definitions**: Show interfaces when implementing or extending
- **Type declarations**: Include custom types being used or extended

#### Transient Details (SHOULD omit with descriptive comments):
- **Previous variable declarations**: Replace with comments like `// Method 1: var declaration with type (from Step 1)`
- **Completed function implementations**: Replace with `// authentication logic from Step 2`
- **Earlier error handling**: Replace with `// error handling implemented in Step 3`
- **Previous output statements**: Replace with `// output formatting from previous steps`

#### Go-Specific Comment Examples:
- `// Package imports and variable declarations from Steps 1-2`
- `// HTTP server setup from Step 1`
- `// Database connection logic from Step 2` 
- `// JSON marshaling functions from Step 3`
- `// Error handling middleware from previous implementation`

#### Step Structure:
- **Step 1**: Complete Go program with package, imports, basic structure
- **Subsequent Steps**: Critical context + descriptive comments + new incremental additions
- **Execute and Verify**: Final step combines `go run` execution with output verification and concept demonstration

### Code Quality Standards

- **Go Standards**: Follow official Go style guide and best practices
- **Error Handling**: Include proper error handling patterns
- **Resource Management**: Demonstrate proper resource cleanup
- **Documentation**: Include clear, practical comments explaining implementation
- **Testing**: Provide testable examples where appropriate

## AECS-Constrained Subagent Usage

### Go Engineer
Use for Go-specific technical implementation:
```
"Implement working Go code that demonstrates [single concept] through practical application. Ensure the Exercise produces tangible results and follows Go best practices."
```

### CS Professor  
Use for Exercise-driven learning validation:
```
"Restructure this content to enforce Exercise Primacy by ensuring learners immediately engage in hands-on Go programming. Verify single-concept atomicity."
```

### Academic Editor
Use for AECS structure enforcement:
```
"Fix any deviations from AECS vocabulary and structure. Ensure content follows Subject→Path→Stage→Concept→Exercise hierarchy for Go programming."
```

## Content Placement Conventions

### Exercise Placement Logic

**Standalone Exercises**: `/standalone/[concept].md`
- Independent concept demonstrations outside the official learning path
- Not part of main progression - exploratory or supplementary concepts
- Example: `/standalone/binary-search-implementation.md`

**Enhancement Exercises**: `/stages/XX-[stage]/enhancements/[concept].md`  
- Expound upon concepts not fully understood within existing Stages
- Supplementary to core Stage progression
- Example: `/stages/02-concurrency/enhancements/goroutine-error-handling.md`

**Stage Integration Exercises**: `/stages/XX-[stage]/XX-[concept].md`
- Add new concept Exercises to existing Stages (updates stage README.md automatically)
- Full integration with Stage progression
- Example: `/stages/04-web-programming/03-json-marshaling.md`