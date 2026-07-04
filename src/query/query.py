from typing import Any, Self, TypeVar

import sqlalchemy
from pydantic import BaseModel
from sqlalchemy import ColumnElement
from sqlalchemy.orm import selectinload
from sqlmodel import Session, SQLModel, and_, func, select
from sqlmodel.sql.expression import SelectOfScalar

from query import BaseFilter

ModelT = TypeVar("ModelT", bound=SQLModel)


class BaseQuery[ModelT: SQLModel]:
    def __init__(self, session: Session, model: type[ModelT]) -> None:
        self._session = session
        self._model = model
        self._joins: list = []
        self._conditions: list[ColumnElement] = []
        self._eager_loads: list = []
        self._limit: int | None = None
        self._offset: int | None = None
        self._joins: list = []
        self._order_by: list = []

    def join(self, *targets) -> Self:
        self._joins.extend(targets)
        return self

    def where(self, *conditions: ColumnElement | Any) -> Self:
        self._conditions.extend(conditions)
        return self

    def filter(self, filter_class: type[BaseFilter], params: BaseModel) -> Self:
        filter_class().apply(self, params)
        return self

    def limit(self, value: int) -> Self:
        self._limit = value
        return self

    def offset(self, value: int) -> Self:
        self._offset = value
        return self

    def eager(self, *relationships) -> Self:
        if not relationships:
            return self

        load = selectinload(relationships[0])  # type: ignore[arg-type]
        for relationship in relationships[1:]:
            load = load.selectinload(relationship)  # type: ignore[arg-type]

        self._eager_loads.append(load)
        return self

    def order_by(self, *columns: Any) -> Self:
        self._order_by.extend(columns)

        return self

    def get(self, id: Any) -> ModelT | None:
        return self._session.get(self._model, id)

    def get_one(self, id: Any) -> ModelT:
        return self._session.get_one(self._model, id)

    def first(self) -> ModelT | None:
        return self._session.exec(self.build()).first()

    def one(self) -> ModelT:
        return self._session.exec(self.build()).one()

    def all(self) -> list[ModelT]:
        return list(self._session.exec(self.build()).all())

    def count(self) -> int:
        base = select(self._model)
        if self._conditions:
            base = base.where(and_(*self._conditions))
        result = self._session.exec(select(func.count()).select_from(base.subquery()))
        return result.one()

    def update(self, **values: Any) -> int:
        stmt = sqlalchemy.update(self._model)
        if self._conditions:
            stmt = stmt.where(and_(*self._conditions))
        stmt = stmt.values(**values)

        result = self._session.exec(stmt)
        return result.rowcount

    def build(self) -> SelectOfScalar[ModelT]:
        statement = select(self._model).select_from(self._model)

        for join in self._joins:
            statement = statement.join(join)

        if self._conditions:
            statement = statement.where(and_(*self._conditions))

        for eager_load in self._eager_loads:
            statement = statement.options(eager_load)

        if self._limit is not None:
            statement = statement.limit(self._limit)

        if self._offset is not None:
            statement = statement.offset(self._offset)

        if len(self._order_by) != 0:
            statement = statement.order_by(*self._order_by)

        return statement
