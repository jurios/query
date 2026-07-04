from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import SQLModel

from query.query import BaseQuery


class TestModel(SQLModel):
    id: int | None = None
    name: str = ""


@pytest.fixture
def query(session: MagicMock) -> BaseQuery:
    return BaseQuery(session, TestModel)


class TestFirst:
    def test_execs_the_built_statement_and_returns_the_first_row(
        self,
        query: BaseQuery,
        session: MagicMock,
    ) -> None:
        statement = object()  # first() must not care what build() returns
        record = TestModel(id=1, name="Ada")
        session.exec.return_value.first.return_value = record

        with patch.object(query, "build", return_value=statement) as build:
            result = query.first()

        build.assert_called_once_with()
        session.exec.assert_called_once_with(statement)
        session.exec.return_value.first.assert_called_once_with()
        assert result is record
