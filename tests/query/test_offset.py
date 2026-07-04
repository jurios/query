from unittest.mock import MagicMock

import pytest
from sqlmodel import Field, SQLModel, select

from query.query import BaseQuery


class Author(SQLModel, table=True):
    __tablename__ = "offset_author"

    id: int | None = Field(default=None, primary_key=True)
    name: str = ""


@pytest.fixture
def query(session: MagicMock) -> BaseQuery:
    return BaseQuery(session, Author)


class TestOffset:
    def test_returns_self_for_chaining(self, query: BaseQuery) -> None:
        assert query.offset(20) is query

    def test_applies_the_offset_to_the_built_statement(self, query: BaseQuery) -> None:
        statement = query.offset(20).build()

        assert statement.compare(select(Author).select_from(Author).offset(20))

    def test_a_fresh_query_has_no_offset(self, query: BaseQuery) -> None:
        statement = query.build()

        assert statement.compare(select(Author).select_from(Author))

    def test_the_last_offset_wins(self, query: BaseQuery) -> None:
        statement = query.offset(20).offset(5).build()

        assert statement.compare(select(Author).select_from(Author).offset(5))
