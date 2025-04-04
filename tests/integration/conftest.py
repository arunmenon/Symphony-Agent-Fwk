"""Configuration for Symphony integration tests."""

import os
import pytest
import dotenv
import asyncio


@pytest.fixture(scope="session", autouse=True)
def load_env():
    """Load environment variables from .env file."""
    dotenv.load_dotenv()
    
    # Verify critical environment variables
    required_vars = ["OPENAI_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        pytest.skip(f"Missing required environment variables: {', '.join(missing)}")


@pytest.fixture(scope="function")
def event_loop():
    """Create an instance of the default event loop for each test."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()