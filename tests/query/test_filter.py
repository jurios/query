from __future__ import annotations

from typing import cast
from unittest.mock import Mock

from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel

from query import BaseFilter, BaseQuery


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)


class UserFilterParams(BaseModel):
    username: str | None = None


class TestBaseQueryFilter:
    def test_instantiates_filter_class_and_applies_it(self) -> None:
        session = cast(Session, Mock(spec=Session))
        query = BaseQuery(session, User)
        params = UserFilterParams(username="michael")

        filter_instance = Mock(spec=BaseFilter)
        filter_instance.apply.return_value = query

        filter_class = Mock(return_value=filter_instance)

        result = query.filter(cast(type[BaseFilter], filter_class), params)

        filter_class.assert_called_once_with()
        filter_instance.apply.assert_called_once_with(query, params)
        assert result is query
