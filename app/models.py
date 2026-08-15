from datetime import UTC, datetime
from decimal import Decimal
from typing import TypeVar
from uuid import UUID, uuid4

from sqlalchemy import DECIMAL, Date, DateTime, String, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Базовый класс модели"""


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), nullable=False, default=uuid4, primary_key=True)
    file_hash: Mapped[str] = mapped_column(String(), nullable=False)
    file_name: Mapped[str] = mapped_column(String(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=True)
    start_date: Mapped[datetime] = mapped_column(Date(), nullable=True)
    end_date: Mapped[datetime] = mapped_column(Date(), nullable=True)
    requirements: Mapped[list[str]] = mapped_column(postgresql.JSONB(none_as_null=True), nullable=True, default=[])
    penalties: Mapped[list[str]] = mapped_column(postgresql.JSONB(none_as_null=True), nullable=True, default=[])
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_error_message: Mapped[str] = mapped_column(String(), nullable=True)


BaseType = TypeVar("BaseType", bound=Base)
