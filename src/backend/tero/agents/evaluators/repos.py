from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .domain import Evaluator


class EvaluatorRepository:

    def __init__(self, db: AsyncSession):
        self._db = db

    async def find_by_id(self, id: int) -> Optional[Evaluator]:
        ret = await self._db.exec(select(Evaluator).where(Evaluator.id == id))
        return ret.one_or_none()

    async def save(self, evaluator: Evaluator) -> Evaluator:
        evaluator = await self._db.merge(evaluator)
        await self._db.commit()
        await self._db.refresh(evaluator)
        return evaluator
