# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot template that combines aiogram 3 (async Telegram bot framework), Django 5 (web framework and ORM), and Celery (background task processing). The architecture is designed for building scalable Telegram bots with persistent user data, admin interface, and background job capabilities.

**Template Context**: When running `/init` on projects based on this template, recognize that this is a starter scaffold. Users will be building actual bots on top of this foundation - the structure here supports extension but the current functionality is intentionally minimal (just a `/start` command and user tracking).

## Essential Commands

### Development Setup
```bash
# Install dependencies
uv sync

# Set up environment
cp .env.example .env  # Then edit .env with your values

# Run database migrations
uv run python manage.py migrate

# (Optional) Create admin superuser
uv run python manage.py createsuperuser
```

### Running Services
```bash
# Start Django development server (for admin interface)
uv run python manage.py runserver

# Start the Telegram bot
uv run python main.py

# Start Celery worker (in separate terminal)
uv run celery -A config worker --loglevel=info
```

### Django Management
```bash
# Create new migrations
uv run python manage.py makemigrations

# Run tests (when implemented)
uv run python manage.py test

# Create Django superuser
uv run python manage.py createsuperuser

# Open Django shell
uv run python manage.py shell
```

### Environment Variables
Key environment variables in `.env`:
- `TELEGRAM_BOT_TOKEN` - Bot token from BotFather (required)
- `DJANGO_SECRET_KEY` - Django secret key (required)
- `CELERY_BROKER_URL` - Redis connection for background jobs
- `START_COMMAND_MESSAGE` - Custom message for `/start` command

## Architecture Overview

### Core Components

**Main Entry Point (`main.py`)**:
- Sets up Django ORM so bot can use database models
- Configures aiogram Bot and Dispatcher
- Registers middleware and routes
- Starts Telegram bot polling

**Django Integration (`config/`)**:
- Standard Django 5 configuration with environment-based settings
- Database configured via `dj-database-url` (defaults to SQLite)
- Celery integration for background tasks
- Admin interface ready for user management

**Bot Logic (`bot/`)**:
- `models.py` - `TelegramUser` model for persistent user storage
- `aiogram/handlers.py` - Telegram message handlers (currently just `/start`)
- `aiogram/middlewares.py` - `UserTrackingMiddleware` that auto-saves users
- `tasks.py` - Celery background tasks (placeholder for development)

### Key Patterns

**User Tracking**: The `UserTrackingMiddleware` automatically captures every user interaction and stores/updates user data in Django database, providing built-in analytics and user management.

**Django + aiogram Integration**: The bot initializes Django setup to use ORM features while maintaining async bot operations. All bot database operations use Django's sync-to-async pattern.

**Extensible Router Structure**: New handlers should be added to `bot.aiogram.handlers` or split into separate router modules that get included in the main dispatcher.

**Background Jobs Ready**: Celery is pre-configured with Redis broker and result backend, with placeholder task structure for scheduling notifications, cleanup, or other async operations.

### Adding Bot Features

**New Commands**: Add handler functions to `bot/aiogram/handlers.py` or create separate router modules and include them in `main.py:42`.

**Database Models**: Add new Django models in `bot/models.py` and register them in `bot/admin.py` for admin interface access.

**Background Tasks**: Implement new Celery tasks in `bot/tasks.py` using the `<REDACTED_USER>_task` decorator.

**Environment Config**: Add new environment variables to `.env.example` and access them via `config/settings.py`.

## Development Notes

- Uses `uv` for dependency management - all commands should be run with `uv run python`
- Django admin interface available at `/admin` when `manage.py runserver` is active
- Database defaults to SQLite but easily configurable via `DATABASE_URL`
- All user interactions are automatically tracked via middleware
- Celery worker runs independently - ensure Redis is running for background tasks
- Template is production-ready but requires proper secret management and database configuration