"""Unit tests for ``BaseQuery.count``.

``count`` wraps the (optionally filtered) model select in a
``select(func.count()).select_from(<subquery>)``, executes it and returns the
single scalar via ``result.one()``. The tests capture the statement handed to
``session.exec`` and compare it (``.compare()`` copes with the subquery's
anonymous alias and is sensitive to the inner WHERE), plus the returned value.
No database is involved.
"""

from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlmodel import Field, SQLModel, and_, col, func, select

from query.query import BaseQuery


class Author(SQLModel, table=True):
    __tablename__ = "count_author"

    id: int | None = Field(default=None, primary_key=True)
    name: str = ""


@pytest.fixture
def query(session: MagicMock) -> BaseQuery:
    """A fresh ``BaseQuery`` over ``Author`` for every test (state isolation)."""
    return BaseQuery(session, Author)


class TestCount:
    def test_returns_the_scalar_count(
        self, query: BaseQuery, session: MagicMock
    ) -> None:
        session.exec.return_value.one.return_value = 7

        assert query.count() == 7

    def test_counts_over_the_model_without_conditions(
        self, query: BaseQuery, session: MagicMock
    ) -> None:
        query.count()

        session.exec.assert_called_once()
        sent = session.exec.call_args.args[0]
        expected = select(func.count()).select_from(select(Author).subquery())
        assert sent.compare(expected)

    def test_applies_conditions_inside_the_counted_subquery(
        self, query: BaseQuery, session: MagicMock
    ) -> None:
        by_name: Any = Author.name == "Ada"
        positive_id: Any = col(Author.id) > 0

        query.where(by_name, positive_id).count()

        sent = session.exec.call_args.args[0]
        base = select(Author).where(and_(by_name, positive_id))
        expected = select(func.count()).select_from(base.subquery())
        assert sent.compare(expected)
