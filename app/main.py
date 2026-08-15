import hashlib
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID

import aiofiles
import structlog
from dishka import AsyncContainer, FromDishka, make_async_container
from dishka.integrations.fastapi import DishkaRoute, FastapiProvider, inject, setup_dishka
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from faststream.rabbit import RabbitBroker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers.custom_json import CustomJSONResponse
from app.helpers.project import get_project_info
from app.middlewares.api_key_header import ApiKeyHeaderMiddleware
from app.middlewares.request_processing_time import RequestProcessingTimeMiddleware
from app.models import Contract
from app.providers import get_providers
from app.schemas import (
    TenderContractCreateResponseSchema,
    TenderContractMessageSchema,
    TenderContractRetrieveResponseSchema,
)
from app.settings import Settings

without_authentication_endpoints = [
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/healthcheck",
]

container: AsyncContainer = make_async_container(*(get_providers() + [FastapiProvider()]))
settings: Settings = container.get_sync(Settings)
log_level = "DEBUG" if settings.app.backend_debug is True else "INFO"
logger = structlog.stdlib.get_logger()
project_info = get_project_info()
broker = RabbitBroker(settings.rabbit_broker_url)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await broker.start()
    yield
    await broker.stop()


app = FastAPI(
    title=project_info["description"],
    version=project_info["version"],
    default_response_class=CustomJSONResponse,
    root_path=settings.app.backend_api_prefix,
    default_route_class=DishkaRoute,
    lifespan=lifespan,
)

app.add_middleware(
    RequestProcessingTimeMiddleware,  # type: ignore[arg-type]
)
app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=settings.cors.cors_origins,
    allow_credentials=settings.cors.cors_allow_credentials,
    allow_methods=settings.cors.cors_allow_methods,
    allow_headers=settings.cors.cors_allow_headers,
)
app.add_middleware(
    ApiKeyHeaderMiddleware,  # type: ignore[arg-type]
    key_value=settings.app.backend_authentication_header_value,
    header_name=settings.app.backend_authentication_header_key,
    ignored_endpoints=without_authentication_endpoints,
)
setup_dishka(container, app)


@app.get("/healthcheck", response_model=dict)
async def health_check():
    """Проверка работоспособности сервиса"""
    return {"status": "healthy"}


@app.post(
    "/tender-contracts",
    summary="Создание тендерного контракта",
    response_model=TenderContractCreateResponseSchema,
)
@inject
async def create_tender_contract(
    file: Annotated[UploadFile, File()],
    request: Request,
    session: FromDishka[AsyncSession],
) -> TenderContractCreateResponseSchema:
    """Создание тендерного контракта"""
    file_path = f"/tmp/{request.state.request_id}.pdf"
    async with aiofiles.open(file_path, "wb+") as out_file:
        while chunk := await file.read(1024 * 1024):
            await out_file.write(chunk)

        await out_file.seek(0)
        content = await out_file.read()
        file_hash = hashlib.sha256(content).hexdigest()

    # Поиск записи в БД по file_hash
    result = await session.execute(select(Contract).where(Contract.file_hash == file_hash))
    existing_contract = result.scalar_one_or_none()

    if existing_contract:
        return TenderContractCreateResponseSchema(id=existing_contract.id)

    # Запись не найдена — публикуем событие для обработки
    await broker.publish(
        TenderContractMessageSchema(
            id=request.state.request_id,
            file_hash=file_hash,
            file_name=file.filename or f"{request.state.request_id}.pdf",
            file_path=file_path,
        ).model_dump(),
        settings.consumer.consumer_queue_name,
    )
    return TenderContractCreateResponseSchema(id=request.state.request_id)


@app.get(
    "/tender-contracts/{entity_id}",
    summary="Получение информации о тендерном контракте",
    response_model=TenderContractRetrieveResponseSchema,
)
@inject
async def retrieve_tender_contract(
    entity_id: str | UUID,
    request: Request,
    session: FromDishka[AsyncSession],
) -> TenderContractRetrieveResponseSchema:
    """Получение информации о тендерном контракте"""
    result = await session.execute(select(Contract).where(Contract.id == entity_id))
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(status_code=404, detail="Контракт не найден")

    return TenderContractRetrieveResponseSchema(
        amount=contract.amount,
        start_date=contract.start_date,
        end_date=contract.end_date,
        requirements=contract.requirements or [],
        penalties=contract.penalties or [],
    )
