# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Testing Commands
- Install: `pip install -e .`
- Run tests: `pytest`
- Run single test: `pytest path/to/test.py::test_function_name`
- Lint code: `ruff check .`
- Type check: `mypy .`

## Code Style Guidelines
- Use **descriptive variable names** that reflect purpose
- Organize imports: stdlib → third-party → local modules
- Use type hints for all function parameters and return values
- Classes use PascalCase, functions/methods use snake_case
- Error handling: prefer explicit error types and messages
- Document public APIs with docstrings (Google style preferred)
- Use Pydantic for data validation and models
- Keep functions small and focused on a single responsibility
- Use async/await for I/O-bound operations
- Follow PEP 8 style guidelines