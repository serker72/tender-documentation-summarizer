from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BaseType

PrimaryKey = int | UUID

ModelT = TypeVar("ModelT", bound=BaseType)


class BaseRepository(Generic[ModelT]):
    """Базовый репозиторий для работы с моделями ORM."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, entity_id: PrimaryKey) -> ModelT | None:
        """Получение записи по первичному ключу."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == entity_id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def add(self, entity: ModelT) -> ModelT:
        """Добавление новой записи в сессию."""
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def commit(self) -> None:
        """Фиксация изменений."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Откат изменений."""
        await self.session.rollback()
