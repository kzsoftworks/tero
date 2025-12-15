import logging
from typing import TYPE_CHECKING, Optional

from langchain_core.messages import HumanMessage

from ..ai_models import ai_factory
if TYPE_CHECKING:
    from ..threads.engine import AgentEngine
from ..usage.domain import Usage


logger = logging.getLogger(__name__)


class QuotaExceededError(Exception):
    pass


class CurrentQuota:
    def __init__(self, current_usage: float, user_quota: float):
        self.current_usage = current_usage
        self.user_quota = user_quota
        

class FileQuota:
    def __init__(self, pdf_parsing_usage: Usage, engine: Optional["AgentEngine"], current_quota: CurrentQuota):
        self.pdf_parsing_usage = pdf_parsing_usage
        self.current_quota = current_quota
        self.model = ai_factory.build_streaming_chat_model(engine._agent.model_id, engine._agent.model_temperature, engine._agent.model_reasoning_effort) if engine else None
        self.available_tokens = engine._agent.model.token_limit - engine._agent.model.output_token_limit if engine else None

    def has_reached_token_limit(self, current_content: str) -> bool:
        if not self.model or not self.available_tokens:
            return False

        current_tokens = self.model.get_num_tokens_from_messages(messages=[HumanMessage(content=current_content)])
        return current_tokens >= self.available_tokens
    
    def has_reached_quota_limit(self) -> bool:
        return self.current_quota.current_usage + self.pdf_parsing_usage.usd_cost > self.current_quota.user_quota
