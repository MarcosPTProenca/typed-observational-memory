# AGENTS.md

This document provides guidelines for agentic coding agents working on the PHP Task Manager project.

## Build / Lint / Test Commands

### Local Development
```bash
# Check PHP syntax for a specific file
php -l path/to/file.php

# Import database schema (local MySQL)
mysql -u root -p < schema.sql

# Import database schema (Docker)
docker-compose exec db mysql -uroot -prootpass < schema.sql
```

### Docker
```bash
# Start containers
docker-compose up -d

# View logs
docker-compose logs -f

# Restart containers
docker-compose restart

# Rebuild containers
docker-compose up -d --build

# Stop containers
docker-compose down

# Clean restart (removes volumes)
docker-compose down -v
```

### Testing
This project uses plain PHP without a testing framework. Manual testing is performed through the web interface at http://localhost:8080 (Docker) or http://localhost/ (local).

## Code Style Guidelines

### File Structure and Naming
- **Classes**: PascalCase (e.g., `Database`, `AuthController`, `TaskController`)
- **Class files**: Must match class name exactly (e.g., `Database.php` contains `class Database`)
- **Methods**: camelCase (e.g., `register()`, `login()`, `getById()`)
- **Properties**: camelCase with appropriate visibility (e.g., `$user`, `$db`, `$connection`)
- **Database tables/columns**: snake_case (e.g., `user_id`, `created_at`, `in_progress`)
- **View files**: lowercase with underscores, organized in subdirectories (e.g., `views/auth/register.php`)

### Import Statements
- Use `require_once` with `__DIR__` for absolute paths to prevent circular includes
- Always require dependencies at the top of files before class definitions
- Example:
  ```php
  require_once __DIR__ . '/../config/database.php';
  require_once __DIR__ . '/../models/User.php';
  ```

### Formatting
- Use 4 spaces for indentation (no tabs)
- Opening braces `{` on the same line as function/class declarations
- Closing braces `}` on their own line
- Space after keywords and control structures: `if ()`, `foreach ()`, `function ()`
- No trailing whitespace at end of lines
- Blank line between methods
- Maximum line length: 120 characters (soft limit)

### Types and Type Safety
- This is a loosely-typed PHP project (no strict types)
- Use PDO::FETCH_ASSOC for database fetch operations
- Always validate and sanitize user input
- Use type hints in method parameters when appropriate for clarity
- Enum values stored as strings in database (e.g., 'pending', 'in_progress', 'completed')

### Naming Conventions
- **Classes**: PascalCase nouns representing entities or controllers
- **Controllers**: End with "Controller" suffix (e.g., `AuthController`, `TaskController`)
- **Models**: Singular nouns representing database entities (e.g., `User`, `Task`)
- **Methods**: Verbs or verb phrases (e.g., `create()`, `update()`, `getByUserId()`)
- **Variables**: camelCase, descriptive names
- **Constants**: UPPER_SNAKE_CASE (e.g., `PDO::ERRMODE_EXCEPTION`)
- **Private properties**: Prefix with `$` and use camelCase
- **Static properties**: Use `$instance` for singleton pattern

### Error Handling
- Always wrap database operations in try-catch blocks
- Use PDO exceptions with `PDO::ERRMODE_EXCEPTION`
- Catch specific exceptions when possible (PDOException)
- Throw generic exceptions from models to controllers
- Collect validation errors in an array for display in views
- Never expose raw database errors to users
- Example:
  ```php
  try {
      $stmt = $this->db->prepare('...');
      $stmt->execute([...]);
  } catch (PDOException $e) {
      if ($e->getCode() == 23000) {
          throw new Exception('Record already exists');
      }
      throw $e;
  }
  ```

### Security Best Practices
- **SQL Injection**: Always use prepared statements with PDO, never concatenate queries
- **XSS Prevention**: Always escape output with `htmlspecialchars()` when displaying user data
- **Password Storage**: Use `password_hash()` and `password_verify()` (never md5/sha1)
- **Session Management**: Start session with `session_start()`, destroy with `session_destroy()`
- **Authentication**: Check `$_SESSION['user_id']` exists before allowing access to protected pages
- **Input Validation**: Trim user input, check for empty values, validate email format, enforce length limits
- **Redirects**: Always use `header('Location: ...')` followed by `exit;` to prevent code execution
- **CSRF Protection**: Not currently implemented, but recommended for production

### Controller Pattern
- Controllers handle HTTP requests and orchestrate business logic
- Check request method (`$_SERVER['REQUEST_METHOD']`) to handle GET vs POST
- Validate input before processing
- Use models for database operations
- Redirect on success, render view on failure
- Always verify user authentication before processing
- Example structure:
  ```php
  public function create() {
      if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
          require __DIR__ . '/../views/task/create.php';
          return;
      }
      
      // Validate input
      // Process with model
      // Redirect on success or render view with errors
  }
  ```

### Model Pattern
- Models encapsulate all database operations for their entity
- Use prepared statements with parameterized queries
- Include user_id in queries to ensure data isolation
- Return arrays for single records, arrays of arrays for multiple
- Use `lastInsertId()` to get created record ID
- Use `rowCount()` to check if update/delete operations affected rows
- Always filter by user_id to prevent unauthorized access
- Example:
  ```php
  public function getById($id, $userId) {
      $stmt = $this->db->prepare('SELECT * FROM tasks WHERE id = ? AND user_id = ?');
      $stmt->execute([$id, $userId]);
      return $stmt->fetch();
  }
  ```

### View Pattern
- Include layout template at the top of each view file
- Use `htmlspecialchars()` for all output escaping
- Access controller-set variables directly in the view
- Use `??` null coalescing operator for optional values
- Keep business logic in controllers, not views
- Use semantic HTML with appropriate classes for styling

### Session Management
- Start session at the beginning of `index.php`
- Store user ID and username in session after successful login
- Check session exists in controllers requiring authentication
- Destroy session on logout
- Never store passwords in session

### Database Configuration
- Use singleton pattern for database connection (Database class)
- Set PDO error mode to EXCEPTION
- Set default fetch mode to ASSOC
- Use UTF-8 charset for database connections
- Handle connection errors gracefully with try-catch

### Docker Configuration
- PHP 8.2 with Apache
- MySQL 8.0 for database
- Environment variables for database credentials
- Volume mounting for live code updates
- Container names: web, db
- Ports: 8080 (web), 3306 (db)

### Adding New Features
1. Update database schema in `schema.sql`
2. Create model in `models/` directory following existing patterns
3. Create controller in `controllers/` directory
4. Create view(s) in `views/` directory
5. Add route handling in `index.php`
6. Update CSS in `public/css/style.css` if needed
7. Test both success and error paths

### Common Gotchas
- Always use `??` null coalescing operator for optional request parameters
- Remember to call `exit` after `header('Location: ...')`
- Use `in_array()` to validate enum values before database operations
- Don't forget to sanitize output in views with `htmlspecialchars()`
- Use `trim()` on text inputs before validation
- Check `$_SERVER['REQUEST_METHOD']` to distinguish GET from POST
- Include `user_id` in all database queries for data isolation