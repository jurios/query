from unittest.mock import MagicMock

from sqlmodel import Field, SQLModel, select  # add `select` to your imports

from query.query import BaseQuery


class Publisher(SQLModel, table=True):
    __tablename__ = "publisher"

    id: int | None = Field(default=None, primary_key=True)


class Author(SQLModel, table=True):
    __tablename__ = "author"

    id: int | None = Field(default=None, primary_key=True)
    publisher_id: int | None = Field(default=None, foreign_key="publisher.id")


class Book(SQLModel, table=True):
    __tablename__ = "book"

    id: int | None = Field(default=None, primary_key=True)
    author_id: int | None = Field(default=None, foreign_key="author.id")


class TestJoin:
    def test_returns_self_for_chaining(self) -> None:
        query = BaseQuery(MagicMock(), Author)

        assert query.join(Book) is query

    def test_applies_a_single_join(self) -> None:
        query = BaseQuery(MagicMock(), Author)

        statement = query.join(Book).build()

        assert statement.compare(select(Author).select_from(Author).join(Book))

    def test_applies_and_orders_multiple_joins_from_a_single_call(self) -> None:
        query = BaseQuery(MagicMock(), Author)

        statement = query.join(Book, Publisher).build()

        assert statement.compare(
            select(Author).select_from(Author).join(Book).join(Publisher)
        )

    def test_accumulates_joins_across_chained_calls(self) -> None:
        query = BaseQuery(MagicMock(), Author)

        statement = query.join(Book).join(Publisher).build()

        assert statement.compare(
            select(Author).select_from(Author).join(Book).join(Publisher)
        )
