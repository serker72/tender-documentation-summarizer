from asyncio import current_task
from collections.abc import AsyncIterator
from typing import AsyncIterable

from dishka import Provider, Scope, provide
from faststream.rabbit.fastapi import RabbitBroker
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)

from app.repositories.contract import ContractRepository
from app.services.contract import ContractService
from app.settings import Settings


class SettingsProvider(Provider):
    @provide(scope=Scope.APP)
    def get_settings(self) -> Settings:
        """Предоставляет экземпляр Settings"""
        return Settings()


class BrokerProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_broker_rabbit(self, settings: Settings) -> AsyncIterator[RabbitBroker]:
        """Предоставляет экземпляр RabbitBroker."""
        broker = RabbitBroker(settings.rabbit_broker_url)
        try:
            await broker.start()
            yield broker
        finally:
            await broker.stop()


class DatabaseProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_async_engine(self, settings: Settings) -> AsyncEngine:
        """Предоставляет экземпляр AsyncEngine."""
        return create_async_engine(
            settings.database_url,
            echo=settings.sqlalchemy.sqlalchemy_debug,
            max_overflow=settings.sqlalchemy.sqlalchemy_max_overflow,
            pool_size=settings.sqlalchemy.sqlalchemy_pool_size,
            pool_timeout=settings.sqlalchemy.sqlalchemy_pool_timeout,
            pool_recycle=settings.sqlalchemy.sqlalchemy_pool_recycle,
            pool_use_lifo=settings.sqlalchemy.sqlalchemy_pool_use_lifo,
            pool_pre_ping=settings.sqlalchemy.sqlalchemy_pool_pre_ping,
        )

    @provide(scope=Scope.APP)
    def provide_async_session_maker(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        """Создание фабрики для AsyncSession."""
        return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    @provide(scope=Scope.REQUEST)
    async def provide_async_session(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> AsyncIterable[AsyncSession]:
        """Предоставляет экземпляр AsyncSession."""
        async_session = async_scoped_session(session_factory=session_factory, scopefunc=current_task)
        try:
            async with async_session() as session:
                yield session
        except Exception:
            await async_session.rollback()
            raise
        finally:
            await async_session.remove()


class AsyncRedisProvider(Provider):
    @provide(scope=Scope.APP)
    def get_async_redis_client(self, settings: Settings) -> Redis:
        """Предоставляет экземпляр Redis."""
        return Redis.from_url(settings.redis_url)


class RepositoryProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_contract_repository(self, session: AsyncSession) -> ContractRepository:
        """Предоставляет экземпляр ContractRepository."""
        return ContractRepository(session=session)


class ServiceProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_contract_service(
        self,
        contract_repository: ContractRepository,
        broker: RabbitBroker,
        settings: Settings,
    ) -> ContractService:
        """Предоставляет экземпляр ContractService."""
        return ContractService(
            contract_repository=contract_repository,
            broker=broker,
            settings=settings,
        )


def get_providers() -> list[Provider]:
    """Получение списка провайдеров Dishka для инъекции зависимостей"""
    return [
        SettingsProvider(),
        BrokerProvider(),
        DatabaseProvider(),
        AsyncRedisProvider(),
        RepositoryProvider(),
        ServiceProvider(),
    ]
