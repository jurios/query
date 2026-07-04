from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import selectinload
from sqlmodel import Field, Relationship, SQLModel, select

from query.query import BaseQuery


# Declared in dependency order (a referenced class must exist before the
# relationship pointing at it) and with test-local table names, so they do not
# clash with models from the other test files sharing SQLModel's registry.
class Publisher(SQLModel, table=True):
    __tablename__ = "eager_publisher"

    id: int | None = Field(default=None, primary_key=True)


class Review(SQLModel, table=True):
    __tablename__ = "eager_review"

    id: int | None = Field(default=None, primary_key=True)
    book_id: int | None = Field(default=None, foreign_key="eager_book.id")


class Book(SQLModel, table=True):
    __tablename__ = "eager_book"

    id: int | None = Field(default=None, primary_key=True)
    title: str = ""
    author_id: int | None = Field(default=None, foreign_key="eager_author.id")
    reviews: list[Review] = Relationship()


class Author(SQLModel, table=True):
    __tablename__ = "eager_author"

    id: int | None = Field(default=None, primary_key=True)
    name: str = ""
    publisher_id: int | None = Field(default=None, foreign_key="eager_publisher.id")
    books: list[Book] = Relationship()
    publisher: Publisher | None = Relationship()


def _selectin(*path: Any) -> Any:
    """Build a (possibly nested) ``selectinload`` option from relationship attrs.

    Mirrors what ``BaseQuery.eager`` does internally. Its ``Any`` parameters
    launder the class-bound relationship attributes (which SQLModel types as the
    instance type, e.g. ``list[Book]``, rather than as a loader-friendly
    descriptor), keeping the expected statements free of per-call type ignores.
    """
    load = selectinload(path[0])
    for attr in path[1:]:
        load = load.selectinload(attr)
    return load


@pytest.fixture
def query(session: MagicMock) -> BaseQuery:
    return BaseQuery(session, Author)


class TestEager:
    def test_returns_self_for_chaining(self, query: BaseQuery) -> None:
        assert query.eager(Author.books) is query

    def test_no_relationships_is_a_noop(self, query: BaseQuery) -> None:
        # eager() with no arguments returns early and attaches nothing.
        statement = query.eager().build()

        assert statement.compare(select(Author).select_from(Author))

    def test_loads_a_single_relationship(self, query: BaseQuery) -> None:
        statement = query.eager(Author.books).build()

        assert statement.compare(
            select(Author).select_from(Author).options(_selectin(Author.books))
        )

    def test_nests_relationships_from_a_single_call(self, query: BaseQuery) -> None:
        statement = query.eager(Author.books, Book.reviews).build()

        assert statement.compare(
            select(Author)
            .select_from(Author)
            .options(_selectin(Author.books, Book.reviews))
        )

    def test_accumulates_separate_loads_across_chained_calls(
        self, query: BaseQuery
    ) -> None:
        statement = query.eager(Author.books).eager(Author.publisher).build()

        assert statement.compare(
            select(Author)
            .select_from(Author)
            .options(_selectin(Author.books))
            .options(_selectin(Author.publisher))
        )

    def test_a_fresh_query_has_no_eager_loads(self, query: BaseQuery) -> None:
        statement = query.build()

        assert statement.compare(select(Author).select_from(Author))
