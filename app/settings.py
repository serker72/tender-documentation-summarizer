from typing import final

from pydantic import AmqpDsn, Field, PostgresDsn, RedisDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


@final
class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_environment: str = Field(description="Окружение проекта")
    backend_debug: bool = Field(False, description="Флаг отладки")
    backend_base_url: str = Field("http://localhost:8000", description="Основной URL")
    backend_api_prefix: str = Field("/api/v1", description="Префикс")
    backend_authentication_header_key: str = Field(description="Заголовок с ключом API")
    backend_authentication_header_value: str = Field(description="Значение ключа API")
    backend_payment_success_rate: float | int = Field(0.9)
    backend_payment_min_delay: int = Field(2)
    backend_payment_max_delay: int = Field(5)
    backend_webhook_retry_attempts: int = Field(3)
    backend_webhook_request_timeout: float | int = Field(10)
    backend_webhook_retry_delay_base: float | int = Field(1.0)
    backend_outbox_poll_interval: float | int = Field(2.0)


@final
class CORSSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cors_origins: list[str] = Field(["http://localhost:3000", "http://localhost:8080"])
    cors_allow_credentials: bool = Field(True)
    cors_allow_methods: list[str] = Field(["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    cors_allow_headers: list[str] = Field(["*"])


@final
class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    postgres_host: str = Field("localhost")
    postgres_port: int = Field(5432)
    postgres_db: str = Field("payment_processing")
    postgres_user: str = Field("payment_processing")
    postgres_password: str = Field("payment_processing")
    postgres_test_db: str = Field("payment_processing_test")
    postgres_test_user: str = Field("payment_processing_test")
    postgres_test_password: str = Field("payment_processing_test")

    @computed_field
    def database_url(self) -> PostgresDsn:
        """Получение URL подключения к серверу PostgreSQL"""
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            path=self.postgres_db,
        )

    @computed_field
    def test_database_url(self) -> PostgresDsn:
        """Получение URL подключения к серверу PostgreSQL, БД test"""
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.postgres_test_user,
            password=self.postgres_test_password,
            host=self.postgres_host,
            port=self.postgres_port,
            path=self.postgres_test_db,
        )


@final
class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_base_url: str = Field("http://localhost:11434", description="Базовый URL Ollama")
    llm_model_name: str = Field("llama3", description="Имя модели LLM")
    llm_prompt: str = Field(
        "Извлеки из текста следующие поля: amount (сумма контракта), start_date (дата начала), "
        "end_date (дата окончания), requirements (ключевые требования), penalties (штрафы). "
        "Ответь в формате JSON.",
        description="Промпт для LLM",
    )


@final
class ConsumerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    consumer_queue_name: str = Field("tender_contracts.new")


@final
class RabbitBrokerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    rabbitmq_username: str = Field("guest")
    rabbitmq_password: str = Field("guest")
    rabbitmq_host: str = Field("localhost")
    rabbitmq_port: int = Field(5672)
    rabbitmq_vhost: str = Field("/")

    @computed_field
    def broker_url(self) -> AmqpDsn:
        """Получение URL подключения к серверу RabbitMQ"""
        return AmqpDsn.build(
            scheme="amqp",
            username=self.rabbitmq_username,
            password=self.rabbitmq_password,
            host=self.rabbitmq_host,
            port=self.rabbitmq_port,
            path=self.rabbitmq_vhost,
        )


@final
class SQLAlchemySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    sqlalchemy_debug: bool = Field(False)
    sqlalchemy_pool_size: int = Field(50)
    sqlalchemy_max_overflow: int = Field(-1)
    sqlalchemy_pool_timeout: float | int = Field(30.0)
    sqlalchemy_pool_recycle: int = Field(600)
    sqlalchemy_pool_use_lifo: bool = Field(False)
    sqlalchemy_pool_pre_ping: bool = Field(True)


@final
class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    redis_username: str = Field("default")
    redis_password: str = Field("")
    redis_host: str = Field("localhost")
    redis_port: int = Field(6379)
    redis_db: int = Field(0)

    @computed_field
    def redis_url(self) -> RedisDsn:
        """Получение URL подключения к серверу Redis"""
        return RedisDsn.build(
            scheme="redis",
            username=self.redis_username if self.redis_username != "default" else None,
            password=self.redis_password if self.redis_password else None,
            host=self.redis_host,
            port=self.redis_port,
            path=str(self.redis_db),
        )


@final
class Settings(BaseSettings):
    app: AppSettings = Field(default_factory=AppSettings)
    consumer: ConsumerSettings = Field(default_factory=ConsumerSettings)
    cors: CORSSettings = Field(default_factory=CORSSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    rabbit_broker: RabbitBrokerSettings = Field(default_factory=RabbitBrokerSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    sqlalchemy: SQLAlchemySettings = Field(default_factory=SQLAlchemySettings)

    @property
    def database_url(self) -> str:
        """Получение URL подключения к серверу PostgreSQL"""
        return str(self.database.database_url)

    @property
    def test_database_url(self) -> str:
        """Получение URL подключения к серверу PostgreSQL, БД test"""
        return str(self.database.test_database_url)

    @property
    def redis_url(self) -> str:
        """Получение URL подключения к серверу Redis"""
        return str(self.redis.redis_url)

    @property
    def rabbit_broker_url(self) -> str:
        """Получение URL подключения к серверу RabbitMQ"""
        return str(self.rabbit_broker.broker_url)
