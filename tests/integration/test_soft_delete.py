"""Behaviour of soft-delete support, verified against both ORMs.

A query that mixes in ``HandlesSoftDeletes`` hides soft-deleted rows by
default, can widen (``with_deleted``) or narrow (``only_deleted``) that scope,
turns ``delete`` into a soft delete, exposes ``force_delete`` for physical
removal, and keeps ``get``/``get_one`` consistent with the active scope.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import ColumnElement, create_engine, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.orm import Session as SASession
from sqlmodel import Field, SQLModel
from sqlmodel import Session as SMSession

from query import BaseQuery, HandlesSoftDeletes


# --- models -------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


class SAUser(Base):
    __tablename__ = "it_sd_sa_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(default="")
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)


class SMUser(SQLModel, table=True):
    __tablename__ = "it_sd_sm_user"

    id: int | None = Field(default=None, primary_key=True)
    name: str = ""
    deleted_at: datetime | None = None


# --- query under test ---------------------------------------------------------
class UserQuery(HandlesSoftDeletes, BaseQuery[Any]):
    def soft_deleted(self) -> ColumnElement:
        return self._model.deleted_at.is_not(None)

    def soft_delete_values(self) -> dict[str, Any]:
        return {"deleted_at": datetime.now(UTC)}


@dataclass
class Backend:
    session: Any
    User: Any


def _seed(session: Any, user_cls: Any) -> None:
    session.add_all(
        [
            user_cls(name="alice"),
            user_cls(name="bob"),
            user_cls(name="carol", deleted_at=datetime.now(UTC)),
        ]
    )
    session.commit()


def _sqlmodel_backend() -> Iterator[Backend]:
    engine = create_engine("sqlite://")
    table = SQLModel.metadata.tables["it_sd_sm_user"]
    SQLModel.metadata.create_all(engine, tables=[table])
    with SMSession(engine) as session:
        _seed(session, SMUser)
        yield Backend(session, SMUser)


def _sqlalchemy_backend() -> Iterator[Backend]:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with SASession(engine) as session:
        _seed(session, SAUser)
        yield Backend(session, SAUser)


@pytest.fixture(params=["sqlmodel", "sqlalchemy"])
def backend(request: pytest.FixtureRequest) -> Iterator[Backend]:
    factory = _sqlmodel_backend if request.param == "sqlmodel" else _sqlalchemy_backend
    yield from factory()


def _query(backend: Backend) -> UserQuery:
    return UserQuery(backend.session, backend.User)


def _id_of(backend: Backend, name: str) -> Any:
    row = (
        backend.session.execute(select(backend.User).where(backend.User.name == name))
        .scalars()
        .one()
    )
    return row.id


class TestScoping:
    def test_default_hides_soft_deleted(self, backend: Backend) -> None:
        names = sorted(u.name for u in _query(backend).all())
        assert names == ["alice", "bob"]

    def test_with_deleted_returns_all(self, backend: Backend) -> None:
        assert _query(backend).with_deleted().count() == 3

    def test_only_deleted_returns_trash(self, backend: Backend) -> None:
        names = [u.name for u in _query(backend).only_deleted().all()]
        assert names == ["carol"]

    def test_count_respects_default_scope(self, backend: Backend) -> None:
        assert _query(backend).count() == 2

    def test_user_conditions_combine_with_scope(self, backend: Backend) -> None:
        rows = _query(backend).where(backend.User.name == "carol").all()
        assert rows == []  # carol is soft-deleted, hidden by default
        rows = _query(backend).with_deleted().where(backend.User.name == "carol").all()
        assert len(rows) == 1


class TestGet:
    def test_get_hides_soft_deleted_by_default(self, backend: Backend) -> None:
        carol_id = _id_of(backend, "carol")
        assert _query(backend).get(carol_id) is None

    def test_get_with_deleted_finds_soft_deleted(self, backend: Backend) -> None:
        carol_id = _id_of(backend, "carol")
        found = _query(backend).with_deleted().get(carol_id)
        assert found is not None and found.name == "carol"

    def test_get_returns_active_row(self, backend: Backend) -> None:
        alice_id = _id_of(backend, "alice")
        assert _query(backend).get(alice_id).name == "alice"

    def test_get_one_raises_when_scope_excludes_row(self, backend: Backend) -> None:
        carol_id = _id_of(backend, "carol")
        with pytest.raises(NoResultFound):
            _query(backend).get_one(carol_id)

    def test_get_one_returns_active_row(self, backend: Backend) -> None:
        bob_id = _id_of(backend, "bob")
        assert _query(backend).get_one(bob_id).name == "bob"


class TestDelete:
    def test_delete_soft_deletes_and_returns_rowcount(self, backend: Backend) -> None:
        affected = _query(backend).where(backend.User.name == "alice").delete()
        backend.session.commit()

        assert affected == 1
        assert _query(backend).count() == 1  # only bob remains active
        assert _query(backend).with_deleted().count() == 3  # nothing was removed

    def test_delete_ignores_already_soft_deleted(self, backend: Backend) -> None:
        # carol is already soft-deleted; default scope excludes her
        affected = _query(backend).where(backend.User.name == "carol").delete()
        backend.session.commit()
        assert affected == 0

    def test_force_delete_removes_physically(self, backend: Backend) -> None:
        affected = _query(backend).only_deleted().force_delete()
        backend.session.commit()

        assert affected == 1  # carol removed for good
        assert _query(backend).with_deleted().count() == 2

    def test_force_delete_respects_scope(self, backend: Backend) -> None:
        # default scope -> only active rows are physically removed
        affected = _query(backend).force_delete()
        backend.session.commit()

        assert affected == 2  # alice + bob
        assert _query(backend).with_deleted().count() == 1  # carol still trashed
