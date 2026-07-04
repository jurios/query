from unittest.mock import MagicMock

from sqlmodel import Field, SQLModel, and_, col

from query.query import BaseQuery


class QueryModel(SQLModel, table=True):
    __tablename__ = "query_model"

    id: int | None = Field(default=None, primary_key=True)
    name: str = ""


class TestWhere:
    def test_returns_self_for_chaining(self) -> None:
        query = BaseQuery(MagicMock(), QueryModel)

        assert query.where(QueryModel.name == "Ada") is query

    def test_applies_a_single_condition_to_the_built_statement(self) -> None:
        query = BaseQuery(MagicMock(), QueryModel)
        condition = QueryModel.name == "Ada"

        statement = query.where(condition).build()

        assert statement.whereclause is not None
        assert statement.whereclause.compare(and_(condition))

    def test_and_combines_multiple_conditions_from_a_single_call(self) -> None:
        query = BaseQuery(MagicMock(), QueryModel)
        by_name = QueryModel.name == "Ada"
        positive_id = col(QueryModel.id) > 0

        statement = query.where(by_name, positive_id).build()

        assert statement.whereclause is not None
        assert statement.whereclause.compare(and_(by_name, positive_id))

    def test_accumulates_conditions_across_chained_calls(self) -> None:
        query = BaseQuery(MagicMock(), QueryModel)
        by_name = QueryModel.name == "Ada"
        positive_id = col(QueryModel.id) > 0

        statement = query.where(by_name).where(positive_id).build()

        assert statement.whereclause is not None
        assert statement.whereclause.compare(and_(by_name, positive_id))
