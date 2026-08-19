"""Behaviour of the row-level lock methods, verified against both ORMs.

Locking is a no-op on SQLite (SQLAlchemy silently omits the clause), so the
generated SQL is asserted by compiling ``build()`` against the PostgreSQL
dialect, while a parallel set of tests confirms the same queries still execute
and return rows unchanged on the in-memory SQLite backend used by the suite.
"""

from __future__ import annotations

from sqlalchemy.dialects import postgresql

from query import BaseQuery

from .conftest import Backend


def _pg_sql(query: BaseQuery) -> str:
    """Render the built statement as PostgreSQL SQL."""
    return str(query.build().compile(dialect=postgresql.dialect()))


class TestForUpdateSQL:
    def test_lock_for_update_appends_for_update(self, backend: Backend) -> None:
        sql = _pg_sql(BaseQuery(backend.session, backend.Author).lock_for_update())

        assert sql.rstrip().endswith("FOR UPDATE")

    def test_nowait(self, backend: Backend) -> None:
        sql = _pg_sql(
            BaseQuery(backend.session, backend.Author).lock_for_update(nowait=True)
        )

        assert "FOR UPDATE NOWAIT" in sql

    def test_skip_locked(self, backend: Backend) -> None:
        sql = _pg_sql(
            BaseQuery(backend.session, backend.Author).lock_for_update(skip_locked=True)
        )

        assert "FOR UPDATE SKIP LOCKED" in sql

    def test_of_restricts_the_lock_to_the_given_entity(self, backend: Backend) -> None:
        sql = _pg_sql(
            BaseQuery(backend.session, backend.Author).lock_for_update(
                of=backend.Author
            )
        )

        assert "FOR UPDATE OF" in sql

    def test_lock_composes_with_where_and_order(self, backend: Backend) -> None:
        sql = _pg_sql(
            BaseQuery(backend.session, backend.Author)
            .where(backend.Author.name == "Ada")
            .order_by(backend.Author.id)
            .lock_for_update()
        )

        assert "WHERE" in sql
        assert "ORDER BY" in sql
        assert sql.rstrip().endswith("FOR UPDATE")


class TestSharedLockSQL:
    def test_shared_lock_appends_for_share(self, backend: Backend) -> None:
        sql = _pg_sql(BaseQuery(backend.session, backend.Author).shared_lock())

        assert sql.rstrip().endswith("FOR SHARE")

    def test_nowait(self, backend: Backend) -> None:
        sql = _pg_sql(
            BaseQuery(backend.session, backend.Author).shared_lock(nowait=True)
        )

        assert "FOR SHARE NOWAIT" in sql


class TestNoLockByDefault:
    def test_plain_query_has_no_lock_clause(self, backend: Backend) -> None:
        sql = _pg_sql(BaseQuery(backend.session, backend.Author))

        assert "FOR UPDATE" not in sql
        assert "FOR SHARE" not in sql


class TestLockedReadsStillExecute:
    """On SQLite the clause is dropped, so reads must behave exactly as usual."""

    def test_lock_for_update_returns_rows(self, backend: Backend) -> None:
        rows = (
            BaseQuery(backend.session, backend.Author)
            .where(backend.Author.name == "Grace")
            .lock_for_update()
            .all()
        )

        assert [row.name for row in rows] == ["Grace"]

    def test_shared_lock_returns_rows(self, backend: Backend) -> None:
        rows = BaseQuery(backend.session, backend.Author).shared_lock().all()

        assert len(rows) == 3

    def test_lock_for_update_one(self, backend: Backend) -> None:
        row = (
            BaseQuery(backend.session, backend.Author)
            .where(backend.Author.name == "Grace")
            .lock_for_update()
            .one()
        )

        assert row.name == "Grace"
