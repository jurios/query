"""Unit tests for ``BaseQuery.order_by``.

``order_by`` accumulates columns (across arguments and across chained calls)
and ``build()`` applies them in order. ``.compare()`` is order sensitive, so
these assertions pin down both the columns and their sequence.
"""

from unittest.mock import MagicMock

import pytest
from sqlmodel import Field, SQLModel, col, select

from query.query import BaseQuery


class Author(SQLModel, table=True):
    __tablename__ = "order_by_author"

    id: int | None = Field(default=None, primary_key=True)
    name: str = ""


@pytest.fixture
def query(session: MagicMock) -> BaseQuery:
    return BaseQuery(session, Author)


class TestOrderBy:
    def test_returns_self_for_chaining(self, query: BaseQuery) -> None:
        assert query.order_by(Author.name) is query

    def test_applies_a_single_ordering(self, query: BaseQuery) -> None:
        statement = query.order_by(Author.name).build()

        assert statement.compare(
            select(Author).select_from(Author).order_by(Author.name)
        )

    def test_preserves_the_order_of_columns_from_one_call(
        self, query: BaseQuery
    ) -> None:
        statement = query.order_by(Author.name, Author.id).build()

        assert statement.compare(
            select(Author).select_from(Author).order_by(Author.name, col(Author.id))
        )

    def test_accumulates_orderings_across_chained_calls(self, query: BaseQuery) -> None:
        statement = query.order_by(Author.name).order_by(Author.id).build()

        assert statement.compare(
            select(Author).select_from(Author).order_by(Author.name, col(Author.id))
        )

    def test_carries_the_descending_direction(self, query: BaseQuery) -> None:

        statement = query.order_by(col(Author.name).desc()).build()

        assert statement.compare(
            select(Author).select_from(Author).order_by(col(Author.name).desc())
        )

    def test_preserves_direction_per_column(self, query: BaseQuery) -> None:
        statement = query.order_by(
            col(Author.name).desc(), col(Author.id).asc()
        ).build()

        assert statement.compare(
            select(Author)
            .select_from(Author)
            .order_by(col(Author.name).desc(), col(Author.id).asc())
        )

    def test_a_fresh_query_has_no_ordering(self, query: BaseQuery) -> None:
        statement = query.build()

        assert statement.compare(select(Author).select_from(Author))
