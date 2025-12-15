from typing import cast

from langchain_core.messages import AIMessage, HumanMessage 
from sqlmodel.ext.asyncio.session import AsyncSession 

from ...ai_models import ai_factory
from ...ai_models.repos import AiModelRepository
from ...core.env import env
from ...threads.domain import MAX_THREAD_NAME_LENGTH
from ...usage.domain import MessageUsage
from ...usage.repos import UsageRepository
from ..domain import Agent


async def generate_test_case_name(
    agent: Agent,
    user_message: str,
    agent_message: str,
    user_id: int,
    db: AsyncSession,
) -> str:
    model = await AiModelRepository(db).find_by_id(env.internal_generator_model)
    if not model:
        raise RuntimeError("Internal generator model not found")

    message_usage = MessageUsage(user_id=user_id, agent_id=agent.id, model_id=model.id)
    try:
        prompt = _build_prompt(agent, user_message, agent_message)
        llm = ai_factory.build_chat_model(model.id, env.internal_generator_temperature)
        response = await llm.ainvoke([HumanMessage(prompt)])
        response = cast(AIMessage, response)
        message_usage.increment_with_metadata(response.usage_metadata, model)
        content = cast(str, response.content).strip()
        if len(content) > MAX_THREAD_NAME_LENGTH:
            content = content[:MAX_THREAD_NAME_LENGTH]
        return content
    finally:
        await UsageRepository(db).add(message_usage)


def _build_prompt(agent: Agent, user_message: str, agent_message: str) -> str:
    agent_name_fragment = (
        f"Agent name: {agent.name}\n" if agent.name else ""
    )
    agent_description_fragment = (
        f"Agent description: {agent.description}\n" if agent.description else ""
    )

    return (
        "You generate descriptive test case titles.\n"
        "Craft a concise, human-friendly title (40 characters or fewer when possible) "
        "that highlights the capability or behavior the user message is asking for. "
        "Focus on the topic being exercised rather than referencing validations or agent responses.\n"
        "Only respond with the title, without quotes or additional text, and do not include the agent name or description.\n\n"
        f"{agent_name_fragment}"
        f"{agent_description_fragment}"
        f"User message: {user_message}\n"
        f"Expected agent response: {agent_message}"
    )
