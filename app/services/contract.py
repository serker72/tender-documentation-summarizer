import hashlib
import json
import os
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import aiofiles
import structlog
from faststream.rabbit import RabbitBroker
from langchain_ollama import ChatOllama

from app.models import Contract
from app.repositories.contract import ContractRepository
from app.schemas import (
    TenderContractCreateResponseSchema,
    TenderContractMessageSchema,
    TenderContractRetrieveResponseSchema,
    TenderContractSchema,
)
from app.settings import Settings

logger = structlog.stdlib.get_logger()


class ContractService:
    """Сервисный слой для бизнес-логики работы с тендерными контрактами."""

    def __init__(
        self,
        contract_repository: ContractRepository,
        broker: RabbitBroker,
        settings: Settings,
    ) -> None:
        self._repository = contract_repository
        self._broker = broker
        self._settings = settings

    # ------------------------------------------------------------------ #
    # API-методы
    # ------------------------------------------------------------------ #

    async def create_contract(
        self,
        file_content: bytes,
        file_name: str,
        request_id: UUID,
    ) -> TenderContractCreateResponseSchema:
        """Создание тендерного контракта: сохранение файла, расчёт хеша, проверка дубликата, публикация события."""
        file_path = f"/tmp/{request_id}.pdf"
        await self.save_uploaded_file(file_path, file_content)

        file_hash = hashlib.sha256(file_content).hexdigest()

        existing_contract = await self._repository.get_by_file_hash(file_hash)
        if existing_contract:
            return TenderContractCreateResponseSchema(id=existing_contract.id)

        await self._broker.publish(
            TenderContractMessageSchema(
                id=request_id,
                file_hash=file_hash,
                file_name=file_name,
                file_path=file_path,
            ).model_dump(),
            self._settings.consumer.consumer_queue_name,
        )
        return TenderContractCreateResponseSchema(id=request_id)

    async def retrieve_contract(self, entity_id: UUID) -> TenderContractRetrieveResponseSchema:
        """Получение информации о тендерном контракте по идентификатору."""
        contract = await self._repository.get_by_id(entity_id)
        if not contract:
            raise ValueError("Контракт не найден")

        return TenderContractRetrieveResponseSchema(
            amount=contract.amount,
            start_date=contract.start_date,
            end_date=contract.end_date,
            requirements=contract.requirements or [],
            penalties=contract.penalties or [],
        )

    # ------------------------------------------------------------------ #
    # Consumer-методы
    # ------------------------------------------------------------------ #

    async def process_contract_message(
        self,
        file_path: str,
        file_hash: str,
        file_name: str,
        entity_id: UUID,
    ) -> None:
        """Обработка сообщения из очереди: извлечение текста, запрос к LLM, сохранение результата."""
        if not file_path or not os.path.exists(file_path):
            logger.error(
                "Файл не найден",
                file_path=file_path,
                file_hash=file_hash,
                entity_id=entity_id,
            )
            return

        try:
            document_text = self._extract_text_from_pdf(file_path)
            parsed = await self._analyze_with_llm(document_text)

            existing = await self._repository.get_by_file_hash(file_hash)
            if existing:
                self._update_contract(existing, parsed)
                logger.info("Контракт обновлён", contract_id=existing.id, file_hash=file_hash)
            else:
                new_contract = self._build_contract(file_hash, file_name, parsed)
                await self._repository.add(new_contract)
                logger.info("Контракт создан", contract_id=new_contract.id, file_hash=file_hash)

            await self._repository.commit()

        except Exception as e:
            logger.error(
                "Ошибка обработки контракта",
                file_path=file_path,
                file_hash=file_hash,
                error=str(e),
                exc_info=True,
            )
            await self._repository.rollback()

        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info("Исходный файл удалён", file_path=file_path)

    # ------------------------------------------------------------------ #
    # Вспомогательные методы
    # ------------------------------------------------------------------ #

    @staticmethod
    def _extract_text_from_pdf(file_path: str) -> str:
        """Извлечение текста из PDF через pypdfium."""
        import pypdfium2 as pdfium

        text_parts = []
        pdf = pdfium.PdfDocument(file_path)
        for page in pdf:
            textpage = page.get_textpage()
            page_text = textpage.get_text_range()
            if page_text:
                text_parts.append(page_text)
            textpage.close()
        pdf.close()
        return "\n".join(text_parts)

    async def _analyze_with_llm(self, document_text: str) -> TenderContractSchema:
        """Запрос к LLM и парсинг результата."""
        llm = ChatOllama(
            model=self._settings.llm.llm_model_name,
            format="json",
            base_url=self._settings.llm.llm_base_url,
        )
        prompt = f"{self._settings.llm.llm_prompt}\n\nТекст документа:\n{document_text}"
        response = await llm.ainvoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        json_str = content.strip()
        if json_str.startswith("```"):
            lines = json_str.split("\n")
            json_str = "\n".join(lines[1:-1])
        llm_data = json.loads(json_str)

        return TenderContractSchema(
            amount=Decimal(str(llm_data["amount"])) if llm_data.get("amount") else None,
            start_date=date.fromisoformat(llm_data["start_date"]) if llm_data.get("start_date") else None,
            end_date=date.fromisoformat(llm_data["end_date"]) if llm_data.get("end_date") else None,
            requirements=llm_data.get("requirements", []),
            penalties=llm_data.get("penalties", []),
        )

    @staticmethod
    def _update_contract(contract: Contract, parsed: TenderContractSchema) -> None:
        """Обновление полей существующего контракта."""
        contract.amount = parsed.amount
        contract.start_date = parsed.start_date
        contract.end_date = parsed.end_date
        contract.requirements = parsed.requirements or []
        contract.penalties = parsed.penalties or []
        contract.processed_at = datetime.now(UTC)

    @staticmethod
    def _build_contract(file_hash: str, file_name: str, parsed: TenderContractSchema) -> Contract:
        """Создание новой сущности контракта."""
        return Contract(
            file_hash=file_hash,
            file_name=file_name or "",
            amount=parsed.amount,
            start_date=parsed.start_date,
            end_date=parsed.end_date,
            requirements=parsed.requirements or [],
            penalties=parsed.penalties or [],
            processed_at=datetime.now(UTC),
        )

    @staticmethod
    async def save_uploaded_file(file_path: str, file_content: bytes) -> None:
        """Сохранение загруженного файла на диск."""
        async with aiofiles.open(file_path, "wb+") as out_file:
            await out_file.write(file_content)
