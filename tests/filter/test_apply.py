from __future__ import annotations

import logging
from typing import Any, cast
from unittest.mock import Mock

import pytest
from pydantic import BaseModel

from query.filter import BaseFilter
from query.query import BaseQuery


class UserFilterParams(BaseModel):
    username: str | None = None
    email: str | None = None
    unsupported: str | None = None


class TestBaseFilter:
    def test_calls_matching_filter_method_with_explicit_value(self) -> None:
        query = cast(BaseQuery[Any], Mock(name="query"))
        params = UserFilterParams(username="michael")

        filter_ = BaseFilter()
        username_filter = Mock(return_value=query)
        setattr(filter_, "username", username_filter)

        result = filter_.apply(query, params)

        username_filter.assert_called_once_with(query, "michael")
        assert result is query

    def test_calls_matching_filter_method_when_value_is_none(self) -> None:
        query = cast(BaseQuery[Any], Mock(name="query"))
        params = UserFilterParams(username=None)

        filter_ = BaseFilter()
        username_filter = Mock(return_value=query)
        setattr(filter_, "username", username_filter)

        result = filter_.apply(query, params)

        username_filter.assert_called_once_with(query, None)
        assert result is query

    def test_does_not_call_filter_method_when_field_was_not_explicitly_received(
        self,
    ) -> None:
        query = cast(BaseQuery[Any], Mock(name="query"))
        params = UserFilterParams(username="michael")

        filter_ = BaseFilter()

        username_filter = Mock(return_value=query)
        email_filter = Mock(return_value=query)

        setattr(filter_, "username", username_filter)
        setattr(filter_, "email", email_filter)

        result = filter_.apply(query, params)

        username_filter.assert_called_once_with(query, "michael")
        email_filter.assert_not_called()
        assert result is query

    def test_ignores_explicit_unsupported_filter_and_logs_debug(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        query = cast(BaseQuery[Any], Mock(name="query"))
        params = UserFilterParams(unsupported="ignored")

        filter_ = BaseFilter()

        with caplog.at_level(logging.DEBUG):
            result = filter_.apply(query, params)

        assert result is query
        assert "Ignoring unsupported filter field 'unsupported'" in caplog.text

    def test_uses_query_returned_by_previous_filter_method(self) -> None:
        initial_query = cast(BaseQuery[Any], Mock(name="initial_query"))
        next_query = cast(BaseQuery[Any], Mock(name="next_query"))

        params = UserFilterParams(
            username="michael",
            email="michael@corleone.test",
        )

        filter_ = BaseFilter()

        username_filter = Mock(return_value=next_query)
        email_filter = Mock(return_value=next_query)

        setattr(filter_, "username", username_filter)
        setattr(filter_, "email", email_filter)

        result = filter_.apply(initial_query, params)

        username_filter.assert_called_once_with(initial_query, "michael")
        email_filter.assert_called_once_with(next_query, "michael@corleone.test")
        assert result is next_query
