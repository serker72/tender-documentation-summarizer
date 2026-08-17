import asyncio
from uuid import UUID

import structlog
from dishka import AsyncContainer, FromDishka, make_async_container
from dishka_faststream import FastStreamProvider, setup_dishka
from faststream.rabbit import RabbitBroker
from faststream.rabbit.annotations import RabbitMessage

from app.providers import get_providers
from app.services.contract import ContractService
from app.settings import Settings

logger = structlog.stdlib.get_logger()

container: AsyncContainer = make_async_container(*(get_providers() + [FastStreamProvider()]))
settings = container.get_sync(Settings)
broker = RabbitBroker(settings.rabbit_broker_url)
setup_dishka(container, broker=broker, auto_inject=True)


@broker.subscriber(queue=settings.consumer.consumer_queue_name)
async def tender_contract_new_handler(
    message: dict,
    raw_message: RabbitMessage,
    contract_service: FromDishka[ContractService],
) -> None:
    """Обработка события создания тендерного контракта"""
    await contract_service.process_contract_message(
        file_path=message.get("file_path", ""),
        file_hash=message.get("file_hash", ""),
        file_name=message.get("file_name", ""),
        entity_id=UUID(message["id"]),
    )


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
