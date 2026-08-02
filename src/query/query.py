from __future__ import annotations

from typing import Any, Self, TypeVar

import sqlalchemy
from pydantic import BaseModel
from sqlalchemy import ColumnElement, Select, and_, func, inspect, select, tuple_
from sqlalchemy.orm import Session, selectinload

from query.filter import BaseFilter

ModelT = TypeVar("ModelT")


class BaseQuery[ModelT]:
    def __init__(self, session: Session, model: type[ModelT]) -> None:
        self._session = session
        self._model = model
        self._joins: list = []
        self._conditions: list[ColumnElement] = []
        self._eager_loads: list = []
        self._limit: int | None = None
        self._offset: int | None = None
        self._order_by: list = []
        self._distinct: bool = False

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

    def distinct(self) -> Self:
        self._distinct = True
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
        return self._session.execute(self.build()).scalars().first()

    def one(self) -> ModelT:
        return self._session.execute(self.build()).scalars().one()

    def all(self) -> list[ModelT]:
        return list(self._session.execute(self.build()).scalars().all())

    def count(self) -> int:
        stmt = select(func.count()).select_from(self._base_select().subquery())
        return self._session.execute(stmt).scalar_one()

    def exists(self) -> bool:
        stmt = select(self._base_select().exists())
        return bool(self._session.execute(stmt).scalar())

    def update(self, **values: Any) -> int:
        stmt = sqlalchemy.update(self._model)
        stmt = self._scope_write(stmt)
        return self._session.execute(stmt.values(**values)).rowcount

    def delete(self) -> int:
        stmt = sqlalchemy.delete(self._model)
        stmt = self._scope_write(stmt)
        return self._session.execute(stmt).rowcount

    def build(self) -> Select[tuple[ModelT]]:
        statement = self._base_select()
        for eager_load in self._eager_loads:
            statement = statement.options(eager_load)
        if self._limit is not None:
            statement = statement.limit(self._limit)
        if self._offset is not None:
            statement = statement.offset(self._offset)
        if self._order_by:
            statement = statement.order_by(*self._order_by)
        return statement

    def _effective_conditions(self) -> list[ColumnElement]:
        return self._conditions

    def _scope_write(self, stmt: Any) -> Any:
        """Restrict a bulk ``UPDATE``/``DELETE`` to the builder's rows.

        With joins we scope by primary key through a subquery; otherwise we
        apply the accumulated conditions directly to keep the simple, common
        path unchanged.
        """
        if self._joins:
            return stmt.where(self._pk_scope())
        conditions = self._effective_conditions()
        if conditions:
            return stmt.where(and_(*conditions))
        return stmt

    def _base_select(self) -> Select[tuple[ModelT]]:
        """Model select with the accumulated joins and conditions applied.

        This is the shared core behind reads, counts and scoped writes, so the
        joins are honoured everywhere instead of only in ``build``.
        """
        statement = select(self._model).select_from(self._model)
        for join in self._joins:
            statement = statement.join(join)
        conditions = self._effective_conditions()
        if conditions:
            statement = statement.where(and_(*conditions))

        if self._distinct:
            statement = statement.distinct()

        return statement

    def _pk_scope(self) -> ColumnElement:
        """Condition matching the builder's rows by primary key.

        A bulk ``UPDATE``/``DELETE`` cannot carry a join portably, so when
        joins are present we scope the write to the primary keys returned by
        the join-aware select instead of dropping the joins silently.
        """
        pk_columns = list(inspect(self._model).primary_key)
        pk_select = self._base_select().with_only_columns(*pk_columns)
        if len(pk_columns) == 1:
            return pk_columns[0].in_(pk_select)
        return tuple_(*pk_columns).in_(pk_select)
