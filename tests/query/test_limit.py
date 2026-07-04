from unittest.mock import MagicMock

import pytest
from sqlmodel import Field, SQLModel, select

from query.query import BaseQuery


class Author(SQLModel, table=True):
    __tablename__ = "limit_author"

    id: int | None = Field(default=None, primary_key=True)
    name: str = ""


@pytest.fixture
def query(session: MagicMock) -> BaseQuery:
    return BaseQuery(session, Author)


class TestLimit:
    def test_returns_self_for_chaining(self, query: BaseQuery) -> None:
        assert query.limit(10) is query

    def test_applies_the_limit_to_the_built_statement(self, query: BaseQuery) -> None:
        statement = query.limit(10).build()

        assert statement.compare(select(Author).select_from(Author).limit(10))

    def test_a_fresh_query_has_no_limit(self, query: BaseQuery) -> None:
        statement = query.build()

        assert statement.compare(select(Author).select_from(Author))

    def test_the_last_limit_wins(self, query: BaseQuery) -> None:
        # limit() overwrites rather than accumulating, so the final call wins.
        statement = query.limit(10).limit(5).build()

        assert statement.compare(select(Author).select_from(Author).limit(5))
