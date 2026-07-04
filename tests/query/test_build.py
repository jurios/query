from unittest.mock import MagicMock

from sqlmodel import Field, SQLModel, Table

from query.query import BaseQuery


class TestModel(SQLModel, table=True):
    __tablename__ = "build_model"

    id: int | None = Field(default=None, primary_key=True)
    name: str = ""


class TestBuild:
    def test_selects_the_model(self) -> None:
        # The session is irrelevant here: build() never touches it.
        query = BaseQuery(MagicMock(), TestModel)

        statement = query.build()

        entities = [col["entity"] for col in statement.column_descriptions]
        assert entities == [TestModel]
        table = statement.get_final_froms()[0]
        assert isinstance(table, Table)
        assert table.name == "build_model"
        assert statement.whereclause is None
