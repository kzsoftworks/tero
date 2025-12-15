import base64
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from langchain_core.messages.ai import UsageMetadata
from pydantic import computed_field
from sqlmodel import Field, SQLModel

from ..ai_models.domain import LlmModel
from ..core.domain import CamelCaseModel
from ..teams.domain import Team


PRIVATE_AGENT_ID = -1


class UsageType(Enum):
    PROMPT_TOKENS = "PROMPT_TOKENS"
    COMPLETION_TOKENS = "COMPLETION_TOKENS"
    PDF_PARSING = "PDF_PARSING"
    WEB_SEARCH = "WEB_SEARCH"
    WEB_EXTRACT = "WEB_EXTRACT"
    EMBEDDING_TOKENS = "EMBEDDING_TOKENS"


class Usage(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True, default=None)
    # We don't add a foreign key to the message so messages can be deleted (when deleting a thread), but usage is kept (for later analysis, reporting, etc.)
    # Additionally, message_id is optional in case the usage is associated with agent configuration
    message_id: Optional[int] = None
    user_id: int = Field(foreign_key="user.id", index=True)
    agent_id: int = Field(foreign_key="agent.id", index=True)
    # we register the model id since agents may change their models or tools may use different models.
    # Additionally, we may want to know how much each model has been used
    model_id: Optional[str] = Field(max_length=30, index=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    quantity: int = 0
    usd_cost: float = 0.0
    type: UsageType = Field()

    def increment(self, new_quantity: int, cost_per_1k_units: float):
        self.quantity += new_quantity
        self.usd_cost += new_quantity / 1000 * cost_per_1k_units


class ToolUsage(CamelCaseModel):
    type: UsageType
    quantity: int
    cost_per_1k_units: float


class MessageUsage():

    def __init__(self, user_id: int, agent_id: int, model_id: str, message_id: Optional[int] = None):
        self.message_id = message_id
        self.user_id = user_id
        self.agent_id = agent_id
        self.model_id = model_id
        self.prompt_usage =  Usage(
                message_id=self.message_id,
                user_id=self.user_id,
                agent_id=self.agent_id,
                model_id=self.model_id,
                type=UsageType.PROMPT_TOKENS
            )
        self.completion_usage = Usage(
                message_id=self.message_id,
                user_id=self.user_id,
                agent_id=self.agent_id,
                model_id=self.model_id,
                type=UsageType.COMPLETION_TOKENS
            )
        self.tools_usage = {}

   
    def increment_with_metadata(self, metadata: Optional[UsageMetadata], model: LlmModel):
        if not metadata:
            return
        self.prompt_usage.increment(metadata["input_tokens"], model.prompt_1k_token_usd)
        self.completion_usage.increment(metadata["output_tokens"], model.completion_1k_token_usd)
    
    def increment_tool_usage(self, tool_usage: Optional[ToolUsage]):
        if not tool_usage:
            return
        if tool_usage.type not in self.tools_usage:
            self.tools_usage[tool_usage.type] = Usage(
                message_id=self.message_id,
                user_id=self.user_id,
                agent_id=self.agent_id,
                model_id=None,
                type=tool_usage.type
            )
        self.tools_usage[tool_usage.type].increment(tool_usage.quantity, tool_usage.cost_per_1k_units)

    
    def usages(self) -> List[Usage]:
        return [self.prompt_usage, self.completion_usage] + list(self.tools_usage.values())
    
    @property
    def usd_cost(self) -> float:
        return sum(usage.usd_cost for usage in self.usages())

class AgentItem(CamelCaseModel):
    agent_id: Optional[int] = None
    agent_name: Optional[str] = None
    icon_bytes: Optional[bytes] = Field(exclude=True)
    icon_bg_color: Optional[str]
    team: Optional[Team] = None
    author_name: Optional[str] = None
    active_users: int
    previous_active_users: int

    @computed_field
    def icon(self) -> Optional[str]:
        return base64.b64encode(self.icon_bytes).decode("utf-8") if self.icon_bytes else None

class UserItem(CamelCaseModel):
    user_id: int
    user_name: Optional[str] = None

class ImpactSummary(CamelCaseModel):
    human_hours: int
    ai_hours: int
    previous_human_hours: int
    previous_ai_hours: int


class AgentImpactItem(AgentItem):
    minutes_saved: int
    previous_minutes_saved: int
    is_external_agent: bool = False


class UserImpactItem(UserItem):
    minutes_saved: int
    monthly_hours: float
    previous_minutes_saved: int


class UsageSummary(CamelCaseModel):
    active_users: int
    total_threads: int
    previous_active_users: int
    previous_total_threads: int


class AgentUsageItem(AgentItem):
    total_threads: int
    previous_total_threads: int


class UserUsageItem(UserItem):
    total_threads: int
    previous_total_threads: int
