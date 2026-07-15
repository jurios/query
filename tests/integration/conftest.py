from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from sqlalchemy import ForeignKey, create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.orm import (
    Session as SASession,
)
from sqlmodel import Field, Relationship, SQLModel
from sqlmodel import Session as SMSession


# --- SQLModel models ----------------------------------------------------------
class SMAuthor(SQLModel, table=True):
    __tablename__ = "it_sm_author"

    id: int | None = Field(default=None, primary_key=True)
    name: str = ""
    books: list["SMBook"] = Relationship(back_populates="author")


class SMBook(SQLModel, table=True):
    __tablename__ = "it_sm_book"

    id: int | None = Field(default=None, primary_key=True)
    title: str = ""
    author_id: int | None = Field(default=None, foreign_key="it_sm_author.id")
    author: SMAuthor | None = Relationship(back_populates="books")
    reviews: list["SMReview"] = Relationship(back_populates="book")


class SMReview(SQLModel, table=True):
    __tablename__ = "it_sm_review"

    id: int | None = Field(default=None, primary_key=True)
    content: str = ""
    book_id: int | None = Field(default=None, foreign_key="it_sm_book.id")
    book: SMBook | None = Relationship(back_populates="reviews")


# --- SQLAlchemy models --------------------------------------------------------
class Base(DeclarativeBase):
    pass


class SAAuthor(Base):
    __tablename__ = "it_sa_author"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(default="")
    books: Mapped[list["SABook"]] = relationship(back_populates="author")


class SABook(Base):
    __tablename__ = "it_sa_book"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(default="")
    author_id: Mapped[int] = mapped_column(ForeignKey("it_sa_author.id"))
    author: Mapped[SAAuthor] = relationship(back_populates="books")
    reviews: Mapped[list["SAReview"]] = relationship(back_populates="book")


class SAReview(Base):
    __tablename__ = "it_sa_review"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(default="")
    book_id: Mapped[int] = mapped_column(ForeignKey("it_sa_book.id"))
    book: Mapped[SABook] = relationship(back_populates="reviews")


@dataclass
class Backend:
    session: Any
    Author: Any
    Book: Any
    Review: Any


def _seed(session: Any, author_cls: Any, book_cls: Any, review_cls: Any) -> None:
    ada = author_cls(name="Ada")
    grace = author_cls(name="Grace")
    ada_bis = author_cls(name="Ada")
    session.add_all([ada, grace, ada_bis])
    session.flush()  # assign author ids

    notes = book_cls(title="Notes on the Engine", author_id=ada.id)
    compiler = book_cls(title="Compiler Design", author_id=grace.id)
    session.add_all([notes, compiler])
    session.flush()  # assign book ids

    session.add_all(
        [
            review_cls(content="Brilliant", book_id=notes.id),
            review_cls(content="Dense but rewarding", book_id=notes.id),
            review_cls(content="A classic", book_id=compiler.id),
        ]
    )
    session.commit()


def _sqlmodel_backend() -> Iterator[Backend]:
    engine = create_engine("sqlite://")
    names = ("it_sm_author", "it_sm_book", "it_sm_review")
    tables = [SQLModel.metadata.tables[name] for name in names]
    SQLModel.metadata.create_all(engine, tables=tables)
    with SMSession(engine) as session:
        _seed(session, SMAuthor, SMBook, SMReview)
        yield Backend(session, SMAuthor, SMBook, SMReview)


def _sqlalchemy_backend() -> Iterator[Backend]:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with SASession(engine) as session:
        _seed(session, SAAuthor, SABook, SAReview)
        yield Backend(session, SAAuthor, SABook, SAReview)


@pytest.fixture(params=["sqlmodel", "sqlalchemy"])
def backend(request: pytest.FixtureRequest) -> Iterator[Backend]:
    factory = _sqlmodel_backend if request.param == "sqlmodel" else _sqlalchemy_backend
    yield from factory()
