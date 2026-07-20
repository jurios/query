from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Self

from sqlalchemy import ColumnElement, Select, and_, inspect, select

if TYPE_CHECKING:
    from query.query import BaseQuery

    # For type checkers only: the mixin is always combined with a BaseQuery,
    # so give it that interface. At runtime the base is ``object`` and the
    # real BaseQuery is reached through the concrete query's MRO.
    _SoftDeleteBase = BaseQuery[Any]
else:
    _SoftDeleteBase = object


class SoftDeleteMode(Enum):
    ACTIVE = auto()  # only non-deleted rows (default)
    WITH_DELETED = auto()  # every row
    ONLY_DELETED = auto()  # only soft-deleted rows


class HandlesSoftDeletes(_SoftDeleteBase):
    """Adds soft-delete awareness to a :class:`BaseQuery`.

    A concrete query mixes this in and defines two things:

    * :meth:`soft_deleted` -- the condition that is *true* for deleted rows
      (the read side), and
    * :meth:`soft_delete_values` -- the values written to mark a row as
      deleted (the write side).

    By default queries only see non-deleted rows. ``with_deleted()`` widens
    to every row and ``only_deleted()`` narrows to the trash. ``delete()``
    becomes a soft delete; ``force_delete()`` removes rows for good.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._soft_delete_mode = SoftDeleteMode.ACTIVE

    def soft_deleted(self) -> ColumnElement:
        """Condition that is true for soft-deleted rows."""
        raise NotImplementedError

    def soft_delete_values(self) -> dict[str, Any]:
        """Values written to mark matching rows as soft-deleted."""
        raise NotImplementedError

    def with_deleted(self) -> Self:
        self._soft_delete_mode = SoftDeleteMode.WITH_DELETED
        return self

    def only_deleted(self) -> Self:
        self._soft_delete_mode = SoftDeleteMode.ONLY_DELETED
        return self

    def _effective_conditions(self) -> list[ColumnElement]:
        conditions = super()._effective_conditions()
        if self._soft_delete_mode is SoftDeleteMode.WITH_DELETED:
            return conditions
        cond = self.soft_deleted()
        if self._soft_delete_mode is SoftDeleteMode.ACTIVE:
            cond = ~cond
        return [*conditions, cond]

    # --- writes --------------------------------------------------------------

    def delete(self) -> int:
        """Soft delete: mark matching rows instead of removing them."""
        return self.update(**self.soft_delete_values())

    def force_delete(self) -> int:
        """Physically delete matching rows."""
        return super().delete()

    def get(self, id: Any) -> Any:
        return self._session.execute(self._get_statement(id)).scalars().first()

    def get_one(self, id: Any) -> Any:
        return self._session.execute(self._get_statement(id)).scalars().one()

    def _get_statement(self, id: Any) -> Select[tuple[Any]]:
        model = self._model
        pk_columns = inspect(model).primary_key
        if len(pk_columns) == 1:
            pk_condition = pk_columns[0] == id
        else:
            pk_condition = and_(
                *(column == value for column, value in zip(pk_columns, id))
            )
        return select(model).where(pk_condition, *self._effective_conditions())
