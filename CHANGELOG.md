# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of Task Crusade MCP
- Campaign and task management system designed for AI coding assistants
- MCP server with 24 tools for campaign and task operations
- Command-line interface (CLI) for task management
- Text User Interface (TUI) for campaign browsing
- SQLite database with automatic migrations via Alembic
- Memory system for AI context management
- Comprehensive integration tests with 76% code coverage
- Support for Python 3.9-3.13

### Features
- **Campaign Management**: Create, update, list, and delete campaigns
- **Task Management**: Full CRUD operations for tasks with dependencies
- **Acceptance Criteria**: Track task completion requirements
- **Research & Notes**: Attach research findings and implementation notes to tasks
- **Testing Steps**: Define testing procedures for tasks
- **Progress Tracking**: Monitor campaign and task completion status
- **Dependency Resolution**: Automatic handling of task dependencies
- **Priority Management**: Critical, high, medium, and low priority levels
- **Status Tracking**: Pending, in-progress, blocked, done, and cancelled statuses

### Security
- SQL injection protection via SQLAlchemy ORM
- Input validation with enum whitelists
- Thread-safe singleton patterns for database connections
- Proper session lifecycle management
- No hardcoded credentials or secrets

### Infrastructure
- Hexagonal architecture with clear separation of concerns
- Domain-driven design with DTOs and result types
- Repository pattern for data access
- Service layer for business logic
- Dependency injection via ServiceFactory
- Comprehensive error handling with DomainResult pattern

## [0.1.0] - TBD

### Added
- Initial public release

[Unreleased]: https://github.com/mcrescenzo/task-crusader-mcp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/mcrescenzo/task-crusader-mcp/releases/tag/v0.1.0
