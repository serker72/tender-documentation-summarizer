from typing import Annotated
from uuid import UUID

import structlog
from dishka import AsyncContainer, FromDishka, make_async_container
from dishka.integrations.fastapi import DishkaRoute, FastapiProvider, inject, setup_dishka
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.helpers.custom_json import CustomJSONResponse
from app.helpers.project import get_project_info
from app.middlewares.api_key_header import ApiKeyHeaderMiddleware
from app.middlewares.request_processing_time import RequestProcessingTimeMiddleware
from app.providers import get_providers
from app.schemas import (
    TenderContractCreateResponseSchema,
    TenderContractRetrieveResponseSchema,
)
from app.services.contract import ContractService
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


app = FastAPI(
    title=project_info["description"],
    version=project_info["version"],
    default_response_class=CustomJSONResponse,
    root_path=settings.app.backend_api_prefix,
    default_route_class=DishkaRoute,
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
    contract_service: FromDishka[ContractService],
) -> TenderContractCreateResponseSchema:
    """Создание тендерного контракта"""
    file_content = await file.read()
    file_name = file.filename or f"{request.state.request_id}.pdf"
    return await contract_service.create_contract(
        file_content=file_content,
        file_name=file_name,
        request_id=request.state.request_id,
    )


@app.get(
    "/tender-contracts/{entity_id}",
    summary="Получение информации о тендерном контракте",
    response_model=TenderContractRetrieveResponseSchema,
)
@inject
async def retrieve_tender_contract(
    entity_id: str | UUID,
    contract_service: FromDishka[ContractService],
) -> TenderContractRetrieveResponseSchema:
    """Получение информации о тендерном контракте"""
    try:
        return await contract_service.retrieve_contract(entity_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Контракт не найден")
