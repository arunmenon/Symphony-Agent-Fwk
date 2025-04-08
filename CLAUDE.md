# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Testing Commands
- Install: `pip install -e .`
- Install with dev dependencies: `pip install -e ".[dev]"`
- Run all tests: `pytest`
- Run specific test category: `pytest -m "unit"` (unit, integration, memory, agents, etc.)
- Run single test: `pytest path/to/test.py::test_function_name`
- Run with coverage: `pytest --cov=symphony`
- Lint code: `ruff check .`
- Type check: `mypy .`
- Auto-format: `black .`

## Code Style Guidelines
- Use **descriptive variable names** that reflect purpose
- Follow imports order: stdlib → third-party → local modules
- Use type hints for all function parameters and return values
- Naming: Classes=PascalCase, functions/methods=snake_case, constants=UPPER_SNAKE_CASE
- Error handling: Use specific error types with clear error messages
- Document public APIs with Google style docstrings
- Use Pydantic BaseModel for data validation and structured objects
- Keep functions focused (single responsibility principle)
- Use async/await for I/O-bound operations
- Apply builder pattern for fluent interfaces
- Follow dependency injection through container system
- Line length: 100 characters max
- Follow PEP 8 style guidelines