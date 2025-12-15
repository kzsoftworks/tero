from typing import Annotated, cast

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from ...core.auth import get_current_user
from ...core.env import env
from ...core.repos import get_db
from ...users.domain import User
from ..api import AGENT_PATH, find_agent_by_id, find_editable_agent
from ..repos import AgentRepository
from ..test_cases.api import TEST_CASE_PATH, find_test_case_by_id
from ..test_cases.repos import TestCaseRepository
from ..test_cases.runner import (
    EVALUATOR_DEFAULT_REASONING_EFFORT,
    EVALUATOR_DEFAULT_TEMPERATURE,
    EVALUATOR_HUMAN_MESSAGE,
)
from .domain import Evaluator, PublicEvaluator
from .repos import EvaluatorRepository


router = APIRouter()
AGENT_EVALUATOR_PATH = f"{AGENT_PATH}/evaluator"


@router.get(AGENT_EVALUATOR_PATH)
async def find_agent_evaluator(agent_id: int, user: Annotated[User, Depends(get_current_user)],
        db: Annotated[AsyncSession, Depends(get_db)]) -> PublicEvaluator:
    agent = await find_agent_by_id(agent_id, user, db)
    evaluator = await EvaluatorRepository(db).find_by_id(agent.evaluator_id) if agent.evaluator_id else None
    if evaluator:
        return PublicEvaluator.from_evaluator(evaluator)
    else:
        return PublicEvaluator(
            model_id=cast(str, env.internal_evaluator_model), 
            temperature=EVALUATOR_DEFAULT_TEMPERATURE, 
            reasoning_effort=EVALUATOR_DEFAULT_REASONING_EFFORT, 
            prompt=EVALUATOR_HUMAN_MESSAGE
        )


@router.put(AGENT_EVALUATOR_PATH)
async def save_agent_evaluator(
    agent_id: int,
    public_evaluator: PublicEvaluator,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> PublicEvaluator:
    agent = await find_editable_agent(agent_id, user, db)
    evaluator_repo = EvaluatorRepository(db)
    
    if agent.evaluator_id:
        evaluator = cast(Evaluator, await evaluator_repo.find_by_id(agent.evaluator_id))
        evaluator.update_with(public_evaluator)
        evaluator = await evaluator_repo.save(evaluator)
        return PublicEvaluator.from_evaluator(evaluator)
    
    evaluator = Evaluator(
        model_id=public_evaluator.model_id,
        temperature=public_evaluator.temperature,
        reasoning_effort=public_evaluator.reasoning_effort,
        prompt=public_evaluator.prompt
    )
    evaluator = await evaluator_repo.save(evaluator)
    
    agent.evaluator_id = evaluator.id
    await AgentRepository(db).update(agent)
    
    return PublicEvaluator.from_evaluator(evaluator)


TEST_CASE_EVALUATOR_PATH = f"{TEST_CASE_PATH}/evaluator"


@router.get(TEST_CASE_EVALUATOR_PATH)
async def find_test_case_evaluator(agent_id: int, test_case_id: int, user: Annotated[User, Depends(get_current_user)],
        db: Annotated[AsyncSession, Depends(get_db)]) -> PublicEvaluator:
    test_case = await find_test_case_by_id(test_case_id, agent_id, user, db)
    evaluator = await EvaluatorRepository(db).find_by_id(test_case.evaluator_id) if test_case.evaluator_id else None
    if evaluator:
        return PublicEvaluator.from_evaluator(evaluator)
    else:
        return await find_agent_evaluator(agent_id, user, db)


@router.put(TEST_CASE_EVALUATOR_PATH)
async def save_test_case_evaluator(
    agent_id: int,
    test_case_id: int,
    public_evaluator: PublicEvaluator,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> PublicEvaluator:
    test_case = await find_test_case_by_id(test_case_id, agent_id, user, db)
    evaluator_repo = EvaluatorRepository(db)
    
    if test_case.evaluator_id:
        evaluator = cast(Evaluator, await evaluator_repo.find_by_id(test_case.evaluator_id))
        evaluator.update_with(public_evaluator)
        evaluator = await evaluator_repo.save(evaluator)
        return PublicEvaluator.from_evaluator(evaluator)
    
    evaluator = Evaluator(
        model_id=public_evaluator.model_id,
        temperature=public_evaluator.temperature,
        reasoning_effort=public_evaluator.reasoning_effort,
        prompt=public_evaluator.prompt
    )
    evaluator = await evaluator_repo.save(evaluator)
    
    test_case.evaluator_id = evaluator.id
    await TestCaseRepository(db).save(test_case)
    
    return PublicEvaluator.from_evaluator(evaluator)
