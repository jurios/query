"""Shared pytest fixtures for the unit-test suite.

These fixtures provide lightweight test doubles so that query/repository
classes can be exercised in complete isolation, without a real database,
engine or connection.
"""

from unittest.mock import MagicMock

import pytest
from sqlmodel import Session


@pytest.fixture
def session() -> MagicMock:
    return MagicMock(spec=Session)
