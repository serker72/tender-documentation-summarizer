from sqlalchemy import select

from app.models import Contract
from app.repositories.base import BaseRepository


class ContractRepository(BaseRepository[Contract]):
    """Репозиторий для работы с контрактами."""

    model = Contract

    async def get_by_file_hash(self, file_hash: str) -> Contract | None:
        """Получение контракта по хешу файла."""
        result = await self.session.execute(select(Contract).where(Contract.file_hash == file_hash))
        return result.scalar_one_or_none()
