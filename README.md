# query

A small, fluent **query builder** for SQLAlchemy — an Eloquent/Laravel-style
query object that wraps a `Session` and a model and lets you read, filter, and
write through a chainable API. It works the same whether your models are plain
[SQLAlchemy](https://www.sqlalchemy.org/) `DeclarativeBase` classes or
[SQLModel](https://sqlmodel.tiangolo.com/) tables, ships declarative
Pydantic-driven filters, and adds opt-in soft-delete support.

```python
active_admins = (
    BaseQuery(session, User)
    .where(User.role == "admin")
    .order_by(User.created_at.desc())
    .limit(10)
    .all()
)
```

## Features

- **Fluent, chainable API** — `where`, `order_by`, `limit`, `offset`, `join`,
  and `eager` return `self`, so queries read top to bottom.
- **Typed** — `BaseQuery[Model]` carries the model type through, so `all()`,
  `first()`, `one()`, `get()` and friends return your model, not `Any`.
- **ORM-agnostic** — the query only depends on the SQLAlchemy `Session` and
  ORM constructs, so the exact same code runs against SQLAlchemy and SQLModel
  models.
- **Declarative filters** — map an incoming Pydantic params object onto query
  conditions, applying only the fields that were actually set.
- **Soft deletes** — an opt-in mixin turns `delete()` into a soft delete,
  scopes reads to active rows by default, and keeps a `force_delete()` escape
  hatch.
- **No magic under the reads** — `build()` hands you the underlying
  `Select` whenever you need to drop down to raw SQLAlchemy.

## Requirements

- Python **3.12+**.
- [SQLAlchemy](https://www.sqlalchemy.org/) **2.0+** (a hard dependency).
- [Pydantic](https://docs.pydantic.dev/) **2** — used by the filter layer, and
  pulled in automatically.
- [SQLModel](https://sqlmodel.tiangolo.com/) is **optional**; install the
  `sqlmodel` extra only if your models are SQLModel tables.

## Installation

The package is not published to PyPI yet, so install it straight from the
repository. With SQLAlchemy models you need nothing extra:

```bash
uv add "git+https://github.com/jurios/query.git"
```

If your models are SQLModel tables, pull in the `sqlmodel` extra:

```bash
uv add "query[sqlmodel] @ git+https://github.com/jurios/query.git"
```

With `pip` the equivalents are:

```bash
pip install "git+https://github.com/jurios/query.git"
pip install "query[sqlmodel] @ git+https://github.com/jurios/query.git"
```

## Quickstart

`BaseQuery` takes a live `Session` and the model class you want to query, then
gives you a chainable builder over it. Define a couple of models, seed some
rows, and query them:

```python
from sqlmodel import Field, Session, SQLModel, create_engine

from query import BaseQuery


class Author(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = ""


engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    session.add_all([Author(name="Ada"), Author(name="Grace")])
    session.commit()

    # Every row, typed as list[Author]
    authors = BaseQuery(session, Author).all()

    # A single, chained query
    grace = (
        BaseQuery(session, Author)
        .where(Author.name == "Grace")
        .first()
    )
    assert grace is not None and grace.name == "Grace"
```

> **Note.** Do not put `from __future__ import annotations` at the top of the
> module where you declare SQLModel models with relationships. It turns the
> relationship annotations into strings that SQLAlchemy cannot resolve
> (`list['Book']`), which fails at mapper configuration time. This is a SQLModel
> constraint, not a `query` one.

## API reference

### Constructing a query

```python
BaseQuery(session, model)
```

- `session` — an active SQLAlchemy `Session` (a SQLModel `Session` works too;
  it is a subclass).
- `model` — the mapped model class to query. `BaseQuery[Model]` is generic, so
  the return types of the read methods below follow the model you pass in.

A query object holds builder state (conditions, joins, ordering, pagination,
eager loads) and is meant to be **built up and then consumed** by a terminal
method. Build a fresh `BaseQuery` per query rather than reusing one across
unrelated reads.

### Shaping the query

Each of these returns `self`, so they chain. They only accumulate state; nothing
hits the database until a terminal read/write method is called.

| Method | Description |
| --- | --- |
| `where(*conditions)` | Add one or more SQLAlchemy conditions. Repeated calls **accumulate** and are combined with `AND`. |
| `order_by(*columns)` | Add ordering columns. Use `Column.desc()` / `.asc()` for direction; multiple columns order left to right. |
| `limit(value)` | Cap the number of rows. The **last** call wins. |
| `offset(value)` | Skip rows (pagination). The **last** call wins. |
| `join(*targets)` | Join related entities so you can filter on their columns (e.g. `join(Book.author)`). Repeated/multiple targets chain. |
| `distinct()` | Deduplicate rows. Handy after a to-many `join`, which repeats parent rows; it also makes `count()` count distinct rows. |
| `eager(*relationships)` | Eager-load relationships with `selectinload`. Pass several arguments to load a **nested** chain (e.g. `eager(Author.books, Book.reviews)`). |
| `filter(filter_class, params)` | Apply a declarative [filter](#declarative-filters) from a Pydantic params object. |

```python
page = (
    BaseQuery(session, Author)
    .where(Author.name == "Ada")
    .order_by(Author.id)
    .limit(10)
    .offset(20)
    .all()
)
```

`join` lets you filter by a related column:

```python
books = (
    BaseQuery(session, Book)
    .join(Book.author)
    .join(Book.reviews)
    .distinct()
    .where(Author.name == "Grace")
    .all()
)
```

`eager` avoids the N+1 problem, and nests when given several relationships:

```python
authors = (
    BaseQuery(session, Author)
    .eager(Author.books, Book.reviews)  # Author -> books -> reviews
    .all()
)
```

### Reading

Terminal methods that execute the built statement and return results:

| Method | Returns | Notes |
| --- | --- | --- |
| `all()` | `list[Model]` | Every matching row. Empty list when nothing matches. |
| `first()` | `Model \| None` | The first matching row, or `None`. |
| `one()` | `Model` | Exactly one row. Raises `NoResultFound` / `MultipleResultsFound` otherwise. |
| `get(id)` | `Model \| None` | Look up by primary key. `None` when missing. |
| `get_one(id)` | `Model` | Look up by primary key. Raises `NoResultFound` when missing. |
| `count()` | `int` | Count rows matching the accumulated conditions and joins. |
| `exists()` | `bool` | Whether any row matches. Stops at the first hit, so it's cheaper than `count() > 0`. Honours joins and soft-delete scoping. |

```python
BaseQuery(session, Author).count()                       # -> 3
BaseQuery(session, Author).where(Author.name == "Ada").count()  # -> 2
BaseQuery(session, Author).get(1)                        # -> Author | None
BaseQuery(session, Author).where(Author.name == "Grace").one()  # -> Author
BaseQuery(session, Author).where(Author.name == "Grace").exists()  # -> True
```

### Writing

Bulk write methods run against the accumulated conditions/joins and return the
number of affected rows.  They emit a single SQL statement and do **not** load
objects into the session, so remember to `commit()`:

| Method | Returns | Notes |
| --- | --- | --- |
| `update(**values)` | `int` | Update matching rows; returns rowcount. With no conditions, updates every row. |
| `delete()` | `int` | Delete matching rows; returns rowcount. With no conditions, deletes every row. |

```python
affected = (
    BaseQuery(session, Author)
    .where(Author.name == "Ada")
    .update(name="Adele")
)
session.commit()
# affected == number of rows that matched
```

> **Careful:** `update()` / `delete()` with no `where` conditions affect the
> **entire table**.

### Escaping to raw SQLAlchemy

`build()` returns the underlying `Select` for the current builder state, so you
can hand it to SQLAlchemy directly when you need something the builder does not
expose:

```python
stmt = BaseQuery(session, Author).where(Author.name == "Ada").build()
rows = session.execute(stmt).scalars().all()
```

## Custom model queries and scopes
 
Because every builder method returns `Self`, you can subclass `BaseQuery[Model]`
to build a **query dedicated to one model** and give it named, reusable
**scopes** — small methods that encapsulate a `where`/`order_by`/… and return
`self` so they keep chaining. This is where the library pays off: intent lives
in the query, and call sites read like a sentence.
 
```python
from typing import Self
 
from query import BaseQuery
 
 
class CarQuery(BaseQuery[Car]):
    def __init__(self, session: Session) -> None:
        # Bake the model in, so callers only pass a session.
        super().__init__(session, Car)
 
    def electrics(self) -> Self:
        return self.where(Car.fuel == "electric")
 
    def doors(self, n: int) -> Self:
        return self.where(Car.doors == n)
 
    def by_brand(self, brand: str) -> Self:
        return self.where(Car.brand == brand)
```
 
Now the scopes chain, and terminate with any of the reading methods:
 
```python
CarQuery(session).electrics().doors(5).all()
CarQuery(session).by_brand("Tesla").electrics().count()
```
 
Two things make this work cleanly:
 
- **Overriding `__init__`** to hardcode the model turns the generic
  `BaseQuery(session, model)` into a domain object you call as
  `CarQuery(session)`. It is optional — you can keep the two-argument form — but
  it is what makes the call sites read as `CarQuery(session).electrics()…`.
- **Returning `Self`** from each scope means the inherited builder methods
  (`where`, `order_by`, `limit`, …) stay available *and* keep their type as
  `CarQuery`, so scopes and built-ins interleave in any order:
```python
recent_electrics = (
    CarQuery(session)
    .electrics()
    .where(Car.brand != "Nissan")   # inherited
    .doors(5)
    .order_by(Car.id.desc())        # inherited
    .limit(10)
    .all()
)
```
 
## Declarative filters

A `BaseFilter` maps the fields of a Pydantic params object onto query
conditions. For each field that was **explicitly set** on the params object, the
filter looks for a method of the same name and calls it with the current query
and the field value; each method returns the (possibly narrowed) query. Fields
that were never set are skipped, and fields with no matching method are ignored
(logged at `DEBUG`).

```python
from pydantic import BaseModel

from query import BaseFilter, BaseQuery


class AuthorParams(BaseModel):
    name: str | None = None


class AuthorFilter(BaseFilter):
    def name(self, query: BaseQuery, value: str) -> BaseQuery:
        return query.where(Author.name == value)


# name is set -> the filter narrows to that name
rows = (
    BaseQuery(session, Author)
    .filter(AuthorFilter, AuthorParams(name="Grace"))
    .all()
)

# name is unset -> the filter changes nothing
everyone = (
    BaseQuery(session, Author)
    .filter(AuthorFilter, AuthorParams())
    .all()
)
```

The "explicitly set" rule uses Pydantic's `model_fields_set`, so passing
`name=None` **does** trigger the `name` method (with `None`), whereas omitting
`name` entirely does not. This lets a single params object drive optional
filtering cleanly — typically straight from a request/query-string model.

## Soft deletes

Mix `HandlesSoftDeletes` into a `BaseQuery` subclass to make deletes reversible.
The concrete query defines two things:

- `soft_deleted()` — the condition that is **true for deleted rows** (the read
  side), and
- `soft_delete_values()` — the values written to mark a row deleted (the write
  side).

```python
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import ColumnElement

from query import BaseQuery, HandlesSoftDeletes


class UserQuery(HandlesSoftDeletes, BaseQuery[User]):
    def soft_deleted(self) -> ColumnElement:
        return self._model.deleted_at.is_not(None)

    def soft_delete_values(self) -> dict[str, Any]:
        return {"deleted_at": datetime.now(UTC)}
```

With that in place:

| Method | Behavior |
| --- | --- |
| *(default scope)* | Reads see **only active** (non-deleted) rows. |
| `with_deleted()` | Widen the scope to **every** row. |
| `only_deleted()` | Narrow the scope to **only soft-deleted** rows. |
| `delete()` | **Soft** delete — writes `soft_delete_values()` instead of removing rows. |
| `force_delete()` | **Physically** delete matching rows (still respecting the current scope). |

```python
# Default scope hides soft-deleted rows
active = UserQuery(session, User).all()

# See everything, or only the trash
UserQuery(session, User).with_deleted().count()
trash = UserQuery(session, User).only_deleted().all()

# delete() soft-deletes; the row is hidden but not gone
UserQuery(session, User).where(User.name == "alice").delete()
session.commit()
UserQuery(session, User).count()                 # alice no longer active
UserQuery(session, User).with_deleted().count()  # ...but still in the table

# force_delete() removes rows for good
UserQuery(session, User).only_deleted().force_delete()
session.commit()
```

The scope also applies to `get()` / `get_one()`, so a soft-deleted row is not
found by primary key unless you widen with `with_deleted()`.

## Works with SQLAlchemy or SQLModel

`BaseQuery` depends only on the SQLAlchemy `Session` and ORM constructs, so the
same query code runs unchanged against plain SQLAlchemy models:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from query import BaseQuery


class Base(DeclarativeBase):
    pass


class Author(Base):
    __tablename__ = "author"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(default="")


engine = create_engine("sqlite://")
Base.metadata.create_all(engine)

with Session(engine) as session:
    session.add_all([Author(name="Ada"), Author(name="Grace")])
    session.commit()

    names = [a.name for a in BaseQuery(session, Author).order_by(Author.id).all()]
    # -> ["Ada", "Grace"]
```

The test suite runs every read, write, and soft-delete behavior against **both**
backends to keep them in lockstep.

## Development

The project uses [uv](https://docs.astral.sh/uv/). Install the toolchain and
dependencies (the dev group already includes SQLModel, so both backends are
available in tests):

```bash
uv sync
```

Run the test suite and the static checks:

```bash
uv run pytest                    # unit tests + SQLModel and SQLAlchemy integration tests
uv run ruff check .              # lint
uv run ruff format --check .     # formatting
```

The integration suites under `tests/integration/` exercise reads, writes, and
soft deletes against a real in-memory SQLite database through both ORMs, so the
ORM-agnostic behavior is verified end to end. SQLite needs no extra system
package — Python ships the `sqlite3` module compiled in.

