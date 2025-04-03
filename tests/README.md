# Symphony Testing Framework

This directory contains tests for the Symphony framework. The tests are organized into unit tests and integration tests.

## Test Structure

- `unit/`: Unit tests for individual components
- `integration/`: Integration tests for multiple components working together
- `conftest.py`: Common fixtures for tests

## Running Tests

To run all tests:

```bash
pytest
```

To run unit tests only:

```bash
pytest tests/unit
```

To run integration tests only:

```bash
pytest tests/integration
```

To run tests with coverage:

```bash
pytest --cov=symphony
```

## Test Categories

Tests are categorized using markers:

- `unit`: Unit tests
- `integration`: Integration tests
- `slow`: Tests that might be slow
- `memory`: Tests related to memory components
- `agents`: Tests related to agent components
- `kg`: Tests related to knowledge graph components
- `dag`: Tests related to DAG workflows
- `orchestration`: Tests related to agent orchestration
- `tools`: Tests related to tools

To run tests with a specific marker:

```bash
pytest -m memory
```

## Writing Tests

When writing tests:

1. Use the fixtures defined in `conftest.py` where possible
2. Mark tests appropriately (unit, integration, component-specific)
3. Use async/await for async functions (with pytest-asyncio)
4. Mock external dependencies
5. Test both success and failure paths

## Testing Async Code

Symphony uses async/await extensively. Use pytest-asyncio for testing:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result == expected_value
```