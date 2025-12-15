from datetime import datetime, timezone
from typing import Any

from sqlmodel import Column, Field, Index, SQLModel, Text

from ...ai_models.domain import LlmTemperature, ReasoningEffort
from ...core.domain import CamelCaseModel


class Evaluator(SQLModel, table=True):
    __tablename__: Any = "evaluator"
    __table_args__ = (
        Index('ix_evaluator_model_id', 'model_id'),
    )
    id: int = Field(primary_key=True, default=None)
    model_id: str = Field(foreign_key="llm_model.id")
    temperature: LlmTemperature = LlmTemperature.NEUTRAL
    reasoning_effort: ReasoningEffort = ReasoningEffort.MEDIUM
    prompt: str = Field(sa_column=Column(Text))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def update_with(self, update: 'PublicEvaluator'):
        self.model_id = update.model_id
        self.temperature = update.temperature
        self.reasoning_effort = update.reasoning_effort
        self.prompt = update.prompt
    
    def clone(self) -> 'Evaluator':
        return Evaluator(
            model_id=self.model_id,
            temperature=self.temperature,
            reasoning_effort=self.reasoning_effort,
            prompt=self.prompt
        )


class PublicEvaluator(CamelCaseModel):
    model_id: str
    temperature: LlmTemperature = LlmTemperature.NEUTRAL
    reasoning_effort: ReasoningEffort = ReasoningEffort.MEDIUM
    prompt: str

    @staticmethod
    def from_evaluator(evaluator: Evaluator) -> 'PublicEvaluator':
        return PublicEvaluator(
            model_id=evaluator.model_id,
            temperature=evaluator.temperature,
            reasoning_effort=evaluator.reasoning_effort,
            prompt=evaluator.prompt
        )
