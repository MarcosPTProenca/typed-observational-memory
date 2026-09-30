# GitHub Copilot Repository Instructions

These instructions guide GitHub Copilot when working within the BudgetWise project.

## Project Context

This is an ASP.NET Core Web API application with a React TypeScript frontend for personal finance and budget tracking, used as a training application for the GitHub Copilot Workshop. The application features a .NET 8 backend with REST APIs and a modern React frontend using Vite, TypeScript, and Tailwind CSS.

## Code Style and Standards

### C# Coding Standards
- Follow standard C# naming conventions (PascalCase for classes/methods/properties, camelCase for local variables/parameters)
- Use meaningful, descriptive names that convey intent
- Keep methods focused and concise (single responsibility principle)
- Prefer composition over inheritance
- Use C# 12 features where appropriate (primary constructors, collection expressions, etc.)
- Use `var` for local variables when the type is obvious
- Place `using` statements inside namespace declarations

### Frontend Guidelines (React/TypeScript)
- Use TypeScript for all new code with strict type checking
- Follow React best practices (hooks, functional components)
- Keep components focused and reusable
- Use Tailwind CSS utility classes for styling
- Avoid inline styles; prefer Tailwind classes
- Use semantic HTML elements
- Follow accessibility best practices (ARIA labels, keyboard navigation)

### ASP.NET Core Best Practices
- Use dependency injection via constructor parameters
- Mark service classes with appropriate lifetimes (Scoped, Singleton, Transient)
- Use minimal API endpoints or controller-based endpoints consistently
- RESTful endpoint naming: use nouns for resources, HTTP methods for actions
- Return `IActionResult` or typed results (e.g., `Ok<T>`, `NotFound`) from controller actions
- Use model validation with Data Annotations
- Leverage built-in middleware for common scenarios (authentication, CORS, etc.)

### Data Transfer Objects (DTOs)
- Create separate DTOs for request/response payloads
- Use `record` types for immutable DTOs
- Include data annotations for validation (`[Required]`, `[MaxLength]`, etc.)
- Map between domain models and DTOs explicitly

### Documentation
- Add XML documentation comments to all public classes and methods
- Include `<summary>`, `<param>`, `<returns>`, and `<exception>` tags where applicable
- Explain WHY, not just WHAT, in comments
- Mark incomplete features with `// TODO:` followed by a clear description

## Testing Guidelines

### Test Structure
- Use xUnit for .NET tests
- Use React Testing Library for frontend tests
- Follow AAA pattern: Arrange, Act, Assert
- Use descriptive test method names: `MethodName_WhenCondition_ThenExpectedResult`

### ASP.NET Core Testing
- Use `WebApplicationFactory<T>` for integration tests
- Mock external dependencies in unit tests
- Test both success and failure scenarios
- Test edge cases and boundary conditions

### React Testing
- Test user interactions, not implementation details
- Use `screen` queries from Testing Library
- Mock API calls with MSW (Mock Service Worker) or similar
- Test accessibility features

## API Design

### REST Endpoints
- Use appropriate HTTP methods: GET (read), POST (create), PUT (update), DELETE (delete)
- Return appropriate status codes (200 OK, 201 Created, 404 Not Found, 400 Bad Request, etc.)
- Use plural nouns for resource endpoints (`/api/expenses`, not `/api/expense`)
- Use path variables for resource IDs: `/api/expenses/{id}`
- Use query parameters for filtering and search: `/api/expenses?category=Food`

### Request/Response
- Use DTOs for complex request/response payloads
- Validate input with Data Annotations or FluentValidation
- Return meaningful error messages in responses
- Use consistent JSON naming (camelCase)
- Include proper Content-Type headers

## Database and Data Access

### Mock Data Strategy
- Use in-memory collections for development and testing
- Populate sample data via `MockData` class in `Data/MockData.cs`
- Keep mock data realistic and representative of production scenarios
- Use thread-safe collections where necessary

### Entity Models
- Use property-based initialization for models
- Include navigation properties for related entities
- Use nullable reference types appropriately (`?` for optional properties)
- Add `required` modifier for mandatory properties in C# 11+

## Workshop-Specific Guidelines

### Intentional Incompleteness
- Some features are intentionally marked with `// TODO` for workshop exercises
- When implementing TODO items, follow existing code patterns
- Write tests for newly implemented features
- Update documentation when adding features

### Learning Focus
- Prioritize code clarity over clever solutions
- Add comments to explain .NET Core and React concepts
- Keep code simple enough for beginners to understand
- Demonstrate best practices, not just working code

## When Generating Code

1. **Check existing patterns**: Look at similar code in the project first
2. **Follow ASP.NET conventions**: Use standard .NET patterns and idioms
3. **Match frontend style**: Follow existing React/TypeScript patterns
4. **Include error handling**: Add appropriate exception handling and validation
5. **Write tests**: Generate tests alongside implementation code
6. **Add documentation**: Include XML docs for public APIs and JSDoc for TypeScript
7. **Validate input**: Use Data Annotations for backend, client-side validation for forms
8. **Return proper responses**: Use typed results with appropriate status codes
9. **Full-stack coherence**: Ensure frontend and backend work together seamlessly

## Prohibited Practices

- ❌ Do not use service locator pattern (always use dependency injection)
- ❌ Do not return null from API endpoints (use `NotFound()` or throw exceptions)
- ❌ Do not put business logic in controllers (use services)
- ❌ Do not ignore exceptions or use empty catch blocks
- ❌ Do not use `any` type in TypeScript (use proper types or `unknown`)
- ❌ Do not create side effects in React component render functions

## Examples

### Good Controller Action
```csharp
/// <summary>
/// Gets an expense by ID.
/// </summary>
/// <param name="id">The expense ID.</param>
/// <returns>The expense if found, otherwise 404 Not Found.</returns>
[HttpGet("{id}")]
public IActionResult GetExpenseById(Guid id)
{
    var expense = _expenseService.GetById(id);
    if (expense == null)
        return NotFound(new { message = $"Expense with ID {id} not found" });
    
    return Ok(expense);
}
```

### Good Service Method
```csharp
public class ExpenseService
{
    private readonly List<Expense> _expenses;

    public ExpenseService()
    {
        _expenses = MockData.Expenses;
    }

    public Expense? GetById(Guid id)
    {
        return _expenses.FirstOrDefault(e => e.Id == id);
    }

    public void Add(Expense expense)
    {
        ArgumentNullException.ThrowIfNull(expense);
        _expenses.Add(expense);
    }
}
```

### Good DTO Definition
```csharp
/// <summary>
/// Request model for creating a new expense.
/// </summary>
public record CreateExpenseRequest
{
    [Required]
    [MaxLength(200)]
    public required string Description { get; init; }

    [Required]
    [Range(0.01, 1000000)]
    public required decimal Amount { get; init; }

    [Required]
    public required DateTime Date { get; init; }

    [Required]
    [MaxLength(50)]
    public required string Category { get; init; }

    [MaxLength(500)]
    public string? Notes { get; init; }
}
```

### Good React Component
```tsx
import { useState } from 'react';
import { Expense } from '../types';
import { api } from '../services/api';

interface ExpenseListProps {
  category?: string;
}

export function ExpenseList({ category }: ExpenseListProps) {
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchExpenses() {
      try {
        setLoading(true);
        const data = category 
          ? await api.getExpensesByCategory(category)
          : await api.getAllExpenses();
        setExpenses(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load expenses');
      } finally {
        setLoading(false);
      }
    }
    
    fetchExpenses();
  }, [category]);

  if (loading) return <div className="text-center">Loading...</div>;
  if (error) return <div className="text-red-600">{error}</div>;

  return (
    <div className="space-y-4">
      {expenses.map(expense => (
        <ExpenseCard key={expense.id} expense={expense} />
      ))}
    </div>
  );
}
```

### Good TypeScript Type Definition
```typescript
/**
 * Represents a financial expense.
 */
export interface Expense {
  id: string;
  userId: string;
  description: string;
  amount: number;
  category: string;
  date: string;
  notes?: string;
  createdAt: string;
  updatedAt?: string;
}

/**
 * Summary of expenses grouped by category.
 */
export interface ExpenseSummary {
  category: string;
  total: number;
  count: number;
  percentage: number;
}
```

## Development Workflow

### Required Commands

#### Backend (.NET)
```bash
cd budgetwise-app/backend
dotnet restore              # Restore dependencies
dotnet build                # Build the project
dotnet run                  # Start the API server (port 5000)
dotnet test                 # Run tests
dotnet watch run            # Run with hot reload
```

#### Frontend (React)
```bash
cd budgetwise-app/frontend
npm install                 # Install dependencies
npm run dev                 # Start dev server with Vite (port 5173)
npm run build               # Production build
npm run preview             # Preview production build
npm run lint                # Run ESLint
npm run test                # Run tests
```

## Key Files for Context

- `budgetwise-app/backend/Program.cs` - Application entry point and middleware configuration
- `budgetwise-app/backend/Controllers/` - REST API endpoint definitions
- `budgetwise-app/backend/Models/` - Domain models and DTOs
- `budgetwise-app/backend/Services/` - Business logic services
- `budgetwise-app/backend/Data/MockData.cs` - Mock data for development
- `budgetwise-app/frontend/src/App.tsx` - Main React application component
- `budgetwise-app/frontend/src/services/api.ts` - API client service
- `budgetwise-app/frontend/src/types/index.ts` - TypeScript type definitions
- `budgetwise-app/README.md` - Comprehensive project documentation
