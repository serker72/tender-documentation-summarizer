from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class TenderContractSchema(BaseModel):
    amount: Decimal | None = Field(default=None, description="Сумма контракта в рублях")
    start_date: date | None = Field(default=None, description="Дата начала работ")
    end_date: date | None = Field(default=None, description="Дата окончания работ")
    requirements: list[str] | None = Field(default_factory=list, description="Ключевые требования к исполнителю")
    penalties: list[str] | None = Field(default_factory=list, description="Список штрафов/неустоек")


class ContractSchema(TenderContractSchema):
    id: UUID = Field(description="ID записи")
    file_hash: str = Field(description="Хеш содержимого файла")
    file_name: str = Field(description="Имя файла")
    processed_at: datetime | None = Field(default=None, description="")
    processing_error_message: str | None = Field(default=None)


class TenderContractMessageSchema(BaseModel):
    id: UUID = Field(description="ID записи")
    file_hash: str = Field(description="Хеш содержимого файла")
    file_name: str = Field(description="Имя файла")
    file_path: str = Field(description="Путь к сохраненному файла")


class TenderContractCreateResponseSchema(BaseModel):
    id: UUID = Field(description="ID контракта")


class TenderContractRetrieveResponseSchema(TenderContractSchema): ...
