from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from .query import BaseQuery, ModelT


logger = logging.getLogger(__name__)


class BaseFilter:
    def apply(self, query: BaseQuery[ModelT], params: BaseModel) -> BaseQuery[ModelT]:
        for field_name in params.__class__.model_fields:
            if field_name not in params.model_fields_set:
                continue

            value = getattr(params, field_name)
            filter_method = getattr(self, field_name, None)

            if filter_method is None:
                logger.debug(
                    "Ignoring unsupported filter field '%s' in %s.",
                    field_name,
                    self.__class__.__name__,
                )
                continue

            if not callable(filter_method):
                raise TypeError(
                    f"Filter attribute '{field_name}' in "
                    f"{self.__class__.__name__} must be callable."
                )

            query = filter_method(query, value)

        return query
