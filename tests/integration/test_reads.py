"""Behaviour of the read operations, verified against both ORMs.

Covers ``all/first/one/get/get_one/count`` and every query-shaping method
(``where/order_by/limit/offset/join/eager/filter``) by asserting *what* comes
back from (or is loaded into) a real database, rather than *how* the session or
statement is built internally.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel
from sqlalchemy.exc import MultipleResultsFound, NoResultFound

from query import BaseFilter, BaseQuery

from .conftest import Backend


class TestAll:
    def test_returns_every_row_as_model_instances(self, backend: Backend) -> None:
        rows = BaseQuery(backend.session, backend.Author).all()

        assert len(rows) == 3
        assert all(isinstance(row, backend.Author) for row in rows)

    def test_returns_empty_list_when_nothing_matches(self, backend: Backend) -> None:
        rows = (
            BaseQuery(backend.session, backend.Author)
            .where(backend.Author.name == "Nobody")
            .all()
        )

        assert rows == []


class TestFirst:
    def test_returns_the_first_match(self, backend: Backend) -> None:
        row = (
            BaseQuery(backend.session, backend.Author)
            .where(backend.Author.name == "Grace")
            .first()
        )

        assert row is not None
        assert row.name == "Grace"

    def test_returns_none_when_empty(self, backend: Backend) -> None:
        row = (
            BaseQuery(backend.session, backend.Author)
            .where(backend.Author.name == "Nobody")
            .first()
        )

        assert row is None


class TestOne:
    def test_returns_the_single_match(self, backend: Backend) -> None:
        row = (
            BaseQuery(backend.session, backend.Author)
            .where(backend.Author.name == "Grace")
            .one()
        )

        assert row.name == "Grace"

    def test_raises_when_no_match(self, backend: Backend) -> None:
        query = BaseQuery(backend.session, backend.Author).where(
            backend.Author.name == "Nobody"
        )

        with pytest.raises(NoResultFound):
            query.one()

    def test_raises_when_multiple_matches(self, backend: Backend) -> None:
        query = BaseQuery(backend.session, backend.Author).where(
            backend.Author.name == "Ada"  # two Adas were seeded
        )

        with pytest.raises(MultipleResultsFound):
            query.one()


class TestGet:
    def test_returns_the_row_by_primary_key(self, backend: Backend) -> None:
        row = BaseQuery(backend.session, backend.Author).get(1)

        assert row is not None
        assert row.id == 1

    def test_returns_none_when_missing(self, backend: Backend) -> None:
        assert BaseQuery(backend.session, backend.Author).get(999) is None


class TestGetOne:
    def test_returns_the_row_by_primary_key(self, backend: Backend) -> None:
        row = BaseQuery(backend.session, backend.Author).get_one(1)

        assert row.id == 1

    def test_raises_when_missing(self, backend: Backend) -> None:
        with pytest.raises(NoResultFound):
            BaseQuery(backend.session, backend.Author).get_one(999)


class TestCount:
    def test_counts_all_rows(self, backend: Backend) -> None:
        assert BaseQuery(backend.session, backend.Author).count() == 3

    def test_counts_only_matching_rows(self, backend: Backend) -> None:
        count = (
            BaseQuery(backend.session, backend.Author)
            .where(backend.Author.name == "Ada")
            .count()
        )

        assert count == 2

    def test_counts_with_a_join_on_a_related_column(self, backend: Backend) -> None:
        # Only Grace (author id=2) wrote a book, so exactly one book matches.
        count = (
            BaseQuery(backend.session, backend.Book)
            .join(backend.Book.author)
            .where(backend.Author.name == "Grace")
            .count()
        )

        assert count == 1

    def test_counts_with_chained_joins_across_two_relationships(
        self, backend: Backend
    ) -> None:
        # Author -> Book -> Review, filtering on the far end. Only Grace's book
        # has the "A classic" review, so exactly one author matches.
        count = (
            BaseQuery(backend.session, backend.Author)
            .join(backend.Author.books)
            .join(backend.Book.reviews)
            .where(backend.Review.content == "A classic")
            .count()
        )

        assert count == 1


class TestWhere:
    def test_filters_rows(self, backend: Backend) -> None:
        rows = (
            BaseQuery(backend.session, backend.Author)
            .where(backend.Author.name == "Ada")
            .all()
        )

        assert {row.name for row in rows} == {"Ada"}
        assert len(rows) == 2

    def test_accumulates_conditions_across_chained_calls(
        self, backend: Backend
    ) -> None:
        rows = (
            BaseQuery(backend.session, backend.Author)
            .where(backend.Author.name == "Ada")
            .where(backend.Author.id == 1)
            .all()
        )

        assert [row.id for row in rows] == [1]


class TestOrderBy:
    def test_ascending(self, backend: Backend) -> None:
        rows = (
            BaseQuery(backend.session, backend.Author).order_by(backend.Author.id).all()
        )

        assert [row.id for row in rows] == [1, 2, 3]

    def test_descending(self, backend: Backend) -> None:
        rows = (
            BaseQuery(backend.session, backend.Author)
            .order_by(backend.Author.id.desc())
            .all()
        )

        assert [row.id for row in rows] == [3, 2, 1]

    def test_mixed_directions_across_columns(self, backend: Backend) -> None:
        # name ascending (Ada, Ada, Grace), and within each name id descending.
        rows = (
            BaseQuery(backend.session, backend.Author)
            .order_by(backend.Author.name.asc(), backend.Author.id.desc())
            .all()
        )

        assert [(row.name, row.id) for row in rows] == [
            ("Ada", 3),
            ("Ada", 1),
            ("Grace", 2),
        ]


class TestLimitOffset:
    def test_limit_and_offset_paginate(self, backend: Backend) -> None:
        rows = (
            BaseQuery(backend.session, backend.Author)
            .order_by(backend.Author.id)
            .limit(1)
            .offset(1)
            .all()
        )

        assert [row.id for row in rows] == [2]

    def test_last_limit_wins(self, backend: Backend) -> None:
        rows = (
            BaseQuery(backend.session, backend.Author)
            .order_by(backend.Author.id)
            .limit(3)
            .limit(1)
            .all()
        )

        assert [row.id for row in rows] == [1]

    def test_last_offset_wins(self, backend: Backend) -> None:
        rows = (
            BaseQuery(backend.session, backend.Author)
            .order_by(backend.Author.id)
            .offset(1)
            .offset(2)
            .all()
        )

        assert [row.id for row in rows] == [3]


class TestJoin:
    def test_filters_by_a_related_column(self, backend: Backend) -> None:
        books = (
            BaseQuery(backend.session, backend.Book)
            .join(backend.Book.author)
            .where(backend.Author.name == "Grace")
            .all()
        )

        assert [book.title for book in books] == ["Compiler Design"]

    def test_chained_joins_across_two_relationships(self, backend: Backend) -> None:
        # Author -> Book -> Review, filtering on the far end.
        authors = (
            BaseQuery(backend.session, backend.Author)
            .join(backend.Author.books)
            .join(backend.Book.reviews)
            .where(backend.Review.content == "A classic")
            .all()
        )

        assert [author.name for author in authors] == ["Grace"]


class TestEager:
    def test_loads_a_single_relationship(self, backend: Backend) -> None:
        authors = (
            BaseQuery(backend.session, backend.Author)
            .eager(backend.Author.books)
            .order_by(backend.Author.id)
            .all()
        )

        # Ada#1 has one book, Grace#2 has one, Ada#3 has none.
        assert [len(author.books) for author in authors] == [1, 1, 0]

    def test_nested_relationships_are_loaded_eagerly(self, backend: Backend) -> None:
        authors = (
            BaseQuery(backend.session, backend.Author)
            .eager(backend.Author.books, backend.Book.reviews)
            .order_by(backend.Author.id)
            .all()
        )

        review_counts = [
            len(book.reviews) for author in authors for book in author.books
        ]
        assert review_counts == [2, 1]  # Ada#1's book: 2 reviews, Grace#2's: 1


class TestFilter:
    def test_applies_a_declarative_filter_end_to_end(self, backend: Backend) -> None:
        author_cls = backend.Author

        class AuthorParams(BaseModel):
            name: str | None = None

        class AuthorFilter(BaseFilter):
            def name(self, query: BaseQuery, value: str) -> BaseQuery:
                return query.where(author_cls.name == value)

        rows = (
            BaseQuery(backend.session, author_cls)
            .filter(AuthorFilter, AuthorParams(name="Grace"))
            .all()
        )

        assert [row.name for row in rows] == ["Grace"]

    def test_unset_fields_are_ignored(self, backend: Backend) -> None:
        author_cls = backend.Author

        class AuthorParams(BaseModel):
            name: str | None = None

        class AuthorFilter(BaseFilter):
            def name(self, query: BaseQuery, value: str) -> BaseQuery:
                return query.where(author_cls.name == value)

        # 'name' was never set, so the filter must not narrow anything.
        rows = (
            BaseQuery(backend.session, author_cls)
            .filter(AuthorFilter, AuthorParams())
            .all()
        )

        assert len(rows) == 3
