# Copilot Instructions for DNSort

## Project Overview

**DNSort** is a sorting algorithm education tool built with Kotlin Multiplatform (Compose Multiplatform). It targets Desktop (JVM) and Web (Wasm/JS).

## Build, Test, and Lint Commands

```bash
# Desktop GUI
./gradlew :composeApp:run

# Web (Wasm - recommended)
./gradlew :composeApp:wasmJsBrowserDevelopmentRun

# Web (JS)
./gradlew :composeApp:jsBrowserDevelopmentRun

# CLI
./gradlew runCli --args="--algorithm bubble --size 20"

# All tests
./gradlew allTests

# Single module tests
./gradlew :domain:allTests
./gradlew :presentation:allTests

# JVM tests only
./gradlew jvmTest

# Lint checks
./gradlew ktlintCheck detekt

# Git hooks setup
./gradlew setupGitHooks
```

## Architecture

Layered Architecture (Clean Architecture-like):

```
Presentation → Domain ← Data
```

- **Domain** has no dependencies on other layers
- **Presentation** and **Data** depend on **Domain**

### Module Structure

| Module | Purpose |
|--------|---------|
| `composeApp/` | Entry points (GUI/CLI) |
| `presentation/` | UI, ViewModel (MVI pattern), Design System (Atomic Design) |
| `domain/` | Algorithms, UseCases, Repository interfaces |
| `data/` | Array generators, Repository implementations |

### Design Patterns

- **Strategy**: `SortAlgorithm` for algorithm switching
- **Factory**: `SortAlgorithmFactory` for instance creation
- **Template Method**: `BaseSortAlgorithm` for shared logic
- **MVI**: ViewModel uses Intent/State for unidirectional data flow

## Key Conventions

### Naming

| Type | Convention | Example |
|------|------------|---------|
| Composable | PascalCase | `SortScreen()` |
| Function | camelCase | `executeSortAlgorithm()` |
| ViewModel | `{Feature}ViewModel` | `SortViewModel` |
| UseCase | `{Verb}{Noun}UseCase` | `ExecuteSortUseCase` |
| Intent (no data) | `data object` | `data object StartSort` |
| Intent (with data) | `data class` | `data class SelectAlgorithm(val type: SortType)` |

### MVI Pattern

```kotlin
// State: immutable data class with val + defaults
data class SortState(
    val algorithm: SortType = SortType.BUBBLE,
    val isLoading: Boolean = false,
    val items: List<Int> = emptyList()  // Use List, not MutableList
)

// StateFlow pattern
private val _state = MutableStateFlow(SortState())
val state: StateFlow<SortState> = _state.asStateFlow()

// Intent dispatch: use send(Intent), never call ViewModel methods directly
```

### Compose Modifier Pattern

```kotlin
<REDACTED_USER>
fun SortBar(
    value: Int,
    modifier: Modifier = Modifier  // Last parameter
) {
    Box(
        modifier = modifier         // External first
            .height(100.dp)         // Internal after
    )
}
```

### Test Naming

Use Given-When-Then with backticks:

```kotlin
<REDACTED_USER>
fun `GIVEN unsorted list WHEN sort is called THEN returns sorted list`() {
    // Given
    val input = listOf(5, 3, 1)
    
    // When
    val result = algorithm.sort(input)
    
    // Then
    assertEquals(listOf(1, 3, 5), result.finalArray)
}
```

### Prohibited Patterns

- `var` in data classes (use `val`)
- `MutableList` in State (use `List`)
- Passing `NavController` to Screen (use callbacks)
- Calling ViewModel methods directly (use `send(Intent)`)
- Hardcoded colors/sizes (use Design Tokens)
- `GlobalScope` (use `viewModelScope`)
- Vague names: `Manager`, `Handler`, `Helper`

## Task-Specific Guides

When implementing features, consult:

| Task | Guide |
|------|-------|
| Add screen | `doc/guide/tasks/ADD_SCREEN.md` |
| Add algorithm | `doc/guide/tasks/ADD_ALGORITHM.md` |
| Add UI component | `doc/guide/tasks/ADD_UI_COMPONENT.md` |
| Add test | `doc/guide/tasks/ADD_TEST.md` |
| Add UseCase | `doc/guide/tasks/ADD_USECASE.md` |
| Add Repository | `doc/guide/tasks/ADD_REPOSITORY.md` |
| Debug | `doc/guide/tasks/DEBUG_GUIDE.md` |

## Branch Naming

```
feature/{PR番号}    # New feature (e.g., feature/01)
bugfix/{Issue番号}  # Bug fix
hotfix/{説明}       # Hotfix
refactor/{説明}     # Refactoring
```

## DI

Uses **Koin** for dependency injection. Modules are registered per layer.