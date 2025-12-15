from typing import Any

from sqlmodel import Field

from ...core.domain import CamelCaseModel


class DocToolFile(CamelCaseModel, table=True):
    __tablename__ : Any = "doc_tool_file"
    agent_id: int = Field(foreign_key="agent.id", primary_key=True)
    file_id: int = Field(foreign_key="file.id", primary_key=True)
    description: str = Field(max_length=200)


class DocToolConfig(CamelCaseModel, table=True):
    __tablename__ : Any = "doc_tool_config"
    agent_id: int = Field(foreign_key="agent.id", primary_key=True)
    description: str = Field(max_length=200)
