from typing import Any
from unittest.mock import MagicMock

import pytest
import sqlalchemy
from sqlmodel import Field, SQLModel, and_, col

from query.query import BaseQuery


class Author(SQLModel, table=True):
    __tablename__ = "update_author"

    id: int | None = Field(default=None, primary_key=True)
    name: str = ""


@pytest.fixture
def query(session: MagicMock) -> BaseQuery:
    return BaseQuery(session, Author)


class TestUpdate:
    def test_returns_the_affected_rowcount(
        self, query: BaseQuery, session: MagicMock
    ) -> None:
        session.exec.return_value.rowcount = 3

        assert query.update(name="new") == 3

    def test_builds_an_update_with_conditions_and_values(
        self, query: BaseQuery, session: MagicMock
    ) -> None:
        by_name: Any = Author.name == "old"
        positive_id: Any = col(Author.id) > 0

        query.where(by_name, positive_id).update(name="new")

        session.exec.assert_called_once()
        sent = session.exec.call_args.args[0]
        expected = (
            sqlalchemy.update(Author)
            .where(and_(by_name, positive_id))
            .values(name="new")
        )
        assert sent.compare(expected)

    def test_without_conditions_targets_every_row(
        self, query: BaseQuery, session: MagicMock
    ) -> None:
        query.update(name="new")

        sent = session.exec.call_args.args[0]
        expected = sqlalchemy.update(Author).values(name="new")
        assert sent.compare(expected)
