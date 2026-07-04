from unittest.mock import MagicMock

import pytest
from sqlmodel import SQLModel

from query.query import BaseQuery


class TestModel(SQLModel):
    id: int | None = None
    name: str = ""


@pytest.fixture
def query(session: MagicMock) -> BaseQuery:
    return BaseQuery(session, TestModel)


class TestGet:
    def test_delegates_to_session_get_with_model_and_identifier(
        self,
        query: BaseQuery,
        session: MagicMock,
    ) -> None:
        query.get(1)

        session.get.assert_called_once_with(TestModel, 1)

    def test_returns_the_record_returned_by_the_session(
        self,
        query: BaseQuery,
        session: MagicMock,
    ) -> None:
        record = TestModel(id=1, name="Ada")
        session.get.return_value = record

        assert query.get(1) is record
