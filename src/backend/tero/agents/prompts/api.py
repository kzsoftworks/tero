import logging
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from ...core.api import BASE_PATH
from ...core.auth import get_current_user
from ...core.repos import get_db
from ...teams.domain import Role, Team
from ...users.domain import User
from ..api import find_agent_by_id
from ..domain import Agent
from .domain import AgentPrompt, AgentPromptCreate, AgentPromptPublic, AgentPromptUpdate
from .repos import AgentPromptRepository

logger = logging.getLogger(__name__)
router = APIRouter()
AGENT_PROMPTS_PATH = f"{BASE_PATH}/agents/{{agent_id}}/prompts"
AGENT_PROMPT_PATH = f"{BASE_PATH}/agents/{{agent_id}}/prompts/{{prompt_id}}"


@router.get(AGENT_PROMPTS_PATH, response_model=list[AgentPromptPublic])
async def find_agent_prompts(
        agent_id: int, user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)],
):
    agent = await find_agent_by_id(agent_id, user, db)
    repo = AgentPromptRepository(db)
    prompts = await repo.find_user_agent_prompts(user.id, agent_id)
    return [_map_public_prompt(agent, user, prompt) for prompt in prompts]


def _map_public_prompt(agent: Agent, user: User, prompt: AgentPrompt):
    public_prompt = AgentPromptPublic.model_validate(prompt)
    public_prompt.can_edit = _is_editable_prompt(prompt, agent, user)
    return public_prompt


def _is_editable_prompt(prompt: AgentPrompt, agent: Agent, user: User) -> bool:
    return prompt.user_id == user.id or (
        prompt.shared and (
            agent.user_id == user.id or 
            (agent.team_id is not None and any(
                tr.role in [Role.TEAM_OWNER, Role.TEAM_EDITOR] and cast(Team, tr.team).id == agent.team_id 
                for tr in user.team_roles
            ))
        )
    )


@router.post(AGENT_PROMPTS_PATH, response_model=AgentPromptPublic, status_code=status.HTTP_201_CREATED)
async def add_agent_prompt(agent_id: int, prompt: AgentPromptCreate, user: Annotated[User, Depends(get_current_user)],
                           db: Annotated[AsyncSession, Depends(get_db)]):
    agent = await find_agent_by_id(agent_id, user, db)
    repo = AgentPromptRepository(db)
    db_prompt = AgentPrompt(name=prompt.name,
                            content=prompt.content, shared=prompt.shared,
                            user_id=user.id, agent_id=agent_id, starter=prompt.starter)
    db_prompt = await repo.add(db_prompt)
    return _map_public_prompt(agent, user, db_prompt)


@router.delete(AGENT_PROMPT_PATH, status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent_prompt(agent_id: int, prompt_id: int, user: Annotated[User, Depends(get_current_user)],
                              db: Annotated[AsyncSession, Depends(get_db)]) -> None:
    agent = await find_agent_by_id(agent_id, user, db)
    repo = AgentPromptRepository(db)
    prompt = await _find_editable_prompt_by_id(prompt_id, agent, user, db)
    await repo.delete(prompt)


async def _find_editable_prompt_by_id(prompt_id: int, agent: Agent, user: User, db):
    prompt = await AgentPromptRepository(db).find_by_id(prompt_id)
    if prompt and _is_editable_prompt(prompt, agent, user):
        return prompt
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")


@router.put(AGENT_PROMPT_PATH, response_model=AgentPromptPublic)
async def update_agent_prompt(agent_id: int, prompt_id: int, updated: AgentPromptUpdate,
                              user: Annotated[User, Depends(get_current_user)],
                              db: Annotated[AsyncSession, Depends(get_db)]):
    agent = await find_agent_by_id(agent_id, user, db)
    repo = AgentPromptRepository(db)
    prompt = await _find_editable_prompt_by_id(prompt_id, agent, user, db)
    prompt.update_with(updated, user.id)
    prompt = await repo.update(prompt)
    return _map_public_prompt(agent, user, prompt)
