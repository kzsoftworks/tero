import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from .domain import ExternalAgent, ExternalAgentTimeSaving, NewExternalAgent, NewExternalAgentTimeSaving, PublicExternalAgent
from .repos import ExternalAgentTimeSavingRepository, ExternalAgentRepository
from ..core.api import BASE_PATH
from ..core.auth import get_current_user
from ..core.repos import get_db
from ..users.domain import User

logger = logging.getLogger(__name__)
router = APIRouter()
EXTERNAL_AGENTS_PATH = f"{BASE_PATH}/external-agents"


@router.get(EXTERNAL_AGENTS_PATH)
async def find_external_agents(
        user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]) -> List[PublicExternalAgent]:
    return [PublicExternalAgent.from_agent(a) for a in await ExternalAgentRepository(db).find_all()]


@router.post(EXTERNAL_AGENTS_PATH)
async def create_external_agent(external_agent: NewExternalAgent,
        user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]) -> ExternalAgent:
    if await ExternalAgentRepository(db).find_by_name(external_agent.name):
        raise HTTPException(status_code=409)
    return await ExternalAgentRepository(db).add(ExternalAgent(
        name=external_agent.name,
        icon=external_agent.icon,
    ))


EXTERNAL_AGENTS_TIME_SAVINGS_PATH = f"{EXTERNAL_AGENTS_PATH}/{{external_agent_id}}/time-savings"


@router.post(EXTERNAL_AGENTS_TIME_SAVINGS_PATH)
async def add_external_agent_time_saving(external_agent_id: int, external_agent_time_saving: NewExternalAgentTimeSaving,
        user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]) -> ExternalAgentTimeSaving:
    await _find_external_agent_by_id(external_agent_id, db)
    return await ExternalAgentTimeSavingRepository(db).add_time_saving(ExternalAgentTimeSaving(
        user_id=user.id,
        external_agent_id=external_agent_id,
        minutes_saved=external_agent_time_saving.minutes_saved,
        date=external_agent_time_saving.date
    ))


async def _find_external_agent_by_id(external_agent_id: int, db: AsyncSession) -> ExternalAgent:
    ret = await ExternalAgentRepository(db).find_by_id(external_agent_id)
    if not ret:
        raise HTTPException(status_code=404)
    return ret