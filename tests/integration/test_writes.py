from __future__ import annotations

from query import BaseQuery

from .conftest import Backend


class TestUpdate:
    def test_updates_matching_rows_and_returns_rowcount(self, backend: Backend) -> None:
        affected = (
            BaseQuery(backend.session, backend.Author)
            .where(backend.Author.name == "Ada")
            .update(name="Adele")
        )
        backend.session.commit()

        assert affected == 2
        assert (
            BaseQuery(backend.session, backend.Author)
            .where(backend.Author.name == "Adele")
            .count()
            == 2
        )

    def test_without_conditions_updates_every_row(self, backend: Backend) -> None:
        affected = BaseQuery(backend.session, backend.Author).update(name="Anon")
        backend.session.commit()

        assert affected == 3
        assert (
            BaseQuery(backend.session, backend.Author)
            .where(backend.Author.name == "Anon")
            .count()
            == 3
        )

    def test_no_match_updates_nothing(self, backend: Backend) -> None:
        affected = (
            BaseQuery(backend.session, backend.Author)
            .where(backend.Author.name == "Nobody")
            .update(name="X")
        )
        backend.session.commit()

        assert affected == 0


class TestDelete:
    def test_deletes_matching_rows_and_returns_rowcount(self, backend: Backend) -> None:
        affected = (
            BaseQuery(backend.session, backend.Author)
            .where(backend.Author.name == "Grace")
            .delete()
        )
        backend.session.commit()

        assert affected == 1
        assert BaseQuery(backend.session, backend.Author).count() == 2

    def test_applies_multiple_conditions(self, backend: Backend) -> None:
        affected = (
            BaseQuery(backend.session, backend.Author)
            .where(backend.Author.name == "Ada", backend.Author.id == 1)
            .delete()
        )
        backend.session.commit()

        assert affected == 1
        assert BaseQuery(backend.session, backend.Author).count() == 2

    def test_no_match_deletes_nothing(self, backend: Backend) -> None:
        affected = (
            BaseQuery(backend.session, backend.Author)
            .where(backend.Author.name == "Nobody")
            .delete()
        )
        backend.session.commit()

        assert affected == 0
        assert BaseQuery(backend.session, backend.Author).count() == 3
