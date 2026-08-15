import asyncio
import json
import os
from datetime import UTC, datetime

import structlog
from dishka import AsyncContainer, FromDishka, make_async_container
from dishka_faststream import FastStreamProvider, setup_dishka
from faststream.rabbit import RabbitBroker
from faststream.rabbit.annotations import RabbitMessage
from langchain_ollama import ChatOllama
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Contract
from app.providers import get_providers
from app.schemas import TenderContractSchema
from app.settings import Settings

logger = structlog.stdlib.get_logger()

container: AsyncContainer = make_async_container(*(get_providers() + [FastStreamProvider()]))
settings = container.get_sync(Settings)
broker = RabbitBroker(settings.rabbit_broker_url)
setup_dishka(container, broker=broker, auto_inject=True)


def extract_text_from_pdf(file_path: str) -> str:
    """Извлечение текста из PDF через pypdfium"""
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


@broker.subscriber(queue=settings.consumer.consumer_queue_name)
async def tender_contract_new_handler(
    message: dict,
    raw_message: RabbitMessage,
    session: FromDishka[AsyncSession],
) -> None:
    """Обработка события создания тендерного контракта"""
    file_path = message.get("file_path")
    file_hash = message.get("file_hash")
    file_name = message.get("file_name")
    entity_id = message.get("id")

    # Проверка наличия файла
    if not file_path or not os.path.exists(file_path):
        logger.error(
            "Файл не найден",
            file_path=file_path,
            file_hash=file_hash,
            entity_id=entity_id,
        )
        return

    try:
        # Загрузка документа
        document_text = extract_text_from_pdf(file_path)

        # Запрос к LLM
        llm = ChatOllama(
            model=settings.llm.llm_model_name,
            format="json",
            base_url=settings.llm.llm_base_url,
        )
        prompt = f"{settings.llm.llm_prompt}\n\nТекст документа:\n{document_text}"
        response = await llm.ainvoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        # Парсинг JSON
        json_str = content.strip()
        if json_str.startswith("```"):
            lines = json_str.split("\n")
            json_str = "\n".join(lines[1:-1])
        llm_data = json.loads(json_str)

        # Парсинг результатов
        from datetime import date
        from decimal import Decimal

        parsed = TenderContractSchema(
            amount=Decimal(str(llm_data["amount"])) if llm_data.get("amount") else None,
            start_date=date.fromisoformat(llm_data["start_date"]) if llm_data.get("start_date") else None,
            end_date=date.fromisoformat(llm_data["end_date"]) if llm_data.get("end_date") else None,
            requirements=llm_data.get("requirements", []),
            penalties=llm_data.get("penalties", []),
        )

        # Проверка, есть ли уже запись
        result = await session.execute(select(Contract).where(Contract.file_hash == file_hash))
        existing = result.scalar_one_or_none()

        if existing:
            existing.amount = parsed.amount
            existing.start_date = parsed.start_date
            existing.end_date = parsed.end_date
            existing.requirements = parsed.requirements or []
            existing.penalties = parsed.penalties or []
            existing.processed_at = datetime.now(UTC)
            logger.info("Контракт обновлён", contract_id=existing.id, file_hash=file_hash)
        else:
            new_contract = Contract(
                file_hash=file_hash,
                file_name=file_name or "",
                amount=parsed.amount,
                start_date=parsed.start_date,
                end_date=parsed.end_date,
                requirements=parsed.requirements or [],
                penalties=parsed.penalties or [],
                processed_at=datetime.now(UTC),
            )
            session.add(new_contract)
            await session.flush()
            logger.info("Контракт создан", contract_id=new_contract.id, file_hash=file_hash)

        await session.commit()

    except Exception as e:
        logger.error(
            "Ошибка обработки контракта",
            file_path=file_path,
            file_hash=file_hash,
            error=str(e),
            exc_info=True,
        )
        await session.rollback()

    finally:
        # Удаление исходного файла после обработки
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info("Исходный файл удалён", file_path=file_path)


async def run_consumer() -> None:
    """Запуск потребителя"""
    logger.info("Consumer starting...")
    await broker.start()
    logger.info("Consumer started")

    try:
        await asyncio.Future()
    except KeyboardInterrupt:
        logger.info("Main Task keyboard interrupt")
    finally:
        logger.info("Consumer shutdown...")
        await broker.stop()
        logger.info("Consumer stopped")


if __name__ == "__main__":
    asyncio.run(run_consumer())
