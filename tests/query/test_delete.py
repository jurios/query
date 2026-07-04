from __future__ import annotations

from typing import cast
from unittest.mock import Mock

import sqlalchemy
from sqlalchemy.sql.dml import Delete
from sqlmodel import Field, Session, SQLModel, and_

from query import BaseQuery


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str
    email: str


class TestBaseQueryDelete:
    def test_delete_executes_delete_statement_for_model(self) -> None:
        session_mock = Mock(spec=Session)

        result_mock = Mock()
        result_mock.rowcount = 3
        session_mock.exec.return_value = result_mock

        query = BaseQuery(cast(Session, session_mock), User)

        deleted_count = query.delete()

        session_mock.exec.assert_called_once()

        statement = cast(Delete, session_mock.exec.call_args.args[0])
        expected_statement = sqlalchemy.delete(User)

        assert statement.table.compare(expected_statement.table)
        assert statement.whereclause is None
        assert deleted_count == 3

    def test_delete_applies_existing_condition(self) -> None:
        session_mock = Mock(spec=Session)

        result_mock = Mock()
        result_mock.rowcount = 1
        session_mock.exec.return_value = result_mock

        query = BaseQuery(cast(Session, session_mock), User)

        condition = User.username == "michael"

        deleted_count = query.where(condition).delete()

        session_mock.exec.assert_called_once()

        statement = cast(Delete, session_mock.exec.call_args.args[0])
        expected_statement = sqlalchemy.delete(User).where(and_(condition))

        assert statement.table.compare(expected_statement.table)
        assert statement.whereclause is not None
        assert expected_statement.whereclause is not None
        assert statement.whereclause.compare(expected_statement.whereclause)
        assert deleted_count == 1

    def test_delete_applies_multiple_existing_conditions(self) -> None:
        session_mock = Mock(spec=Session)

        result_mock = Mock()
        result_mock.rowcount = 1
        session_mock.exec.return_value = result_mock

        query = BaseQuery(cast(Session, session_mock), User)

        username_condition = User.username == "michael"
        email_condition = User.email == "michael@corleone.test"

        deleted_count = query.where(
            username_condition,
            email_condition,
        ).delete()

        session_mock.exec.assert_called_once()

        statement = cast(Delete, session_mock.exec.call_args.args[0])
        expected_statement = sqlalchemy.delete(User).where(
            and_(
                username_condition,
                email_condition,
            )
        )

        assert statement.table.compare(expected_statement.table)
        assert statement.whereclause is not None
        assert expected_statement.whereclause is not None
        assert statement.whereclause.compare(expected_statement.whereclause)
        assert deleted_count == 1
