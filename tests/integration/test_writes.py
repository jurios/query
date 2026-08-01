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

    def test_updates_only_the_joined_rows(self, backend: Backend) -> None:
        affected = (
            BaseQuery(backend.session, backend.Book)
            .join(backend.Book.author)
            .where(backend.Author.name == "Grace")
            .update(title="Renamed")
        )
        backend.session.commit()

        assert affected == 1
        titles = {b.title for b in BaseQuery(backend.session, backend.Book).all()}
        assert titles == {"Renamed", "Notes on the Engine"}


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

    def test_deletes_only_the_joined_rows(self, backend: Backend) -> None:
        # Deleting through a join must remove only Grace's book and leave
        # Ada's book ("Notes on the Engine") in place.
        affected = (
            BaseQuery(backend.session, backend.Book)
            .join(backend.Book.author)
            .where(backend.Author.name == "Grace")
            .delete()
        )
        backend.session.commit()

        assert affected == 1
        titles = {b.title for b in BaseQuery(backend.session, backend.Book).all()}
        assert titles == {"Notes on the Engine"}
