"""
Minimal conftest for unit tests.

This conftest does NOT import the main application, allowing unit tests
to run in isolation with just mocks and the minimal required imports.

IMPORTANT: This file must set environment variables BEFORE any gateway imports
to prevent pydantic settings validation errors.
"""

import sys
import os

# Set environment variables BEFORE importing pytest or any gateway modules
# These must be set before pydantic-settings tries to validate
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"

# Ensure the gateway module can be found
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest


@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio as the async backend."""
    return "asyncio"


# Block the root conftest from being loaded
# by providing a marker that the unit tests are using their own conftest
collect_ignore_glob = ["../conftest.py"]
