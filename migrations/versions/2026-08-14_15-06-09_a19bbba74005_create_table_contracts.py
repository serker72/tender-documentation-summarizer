"""create table contracts

Revision ID: a19bbba74005
Revises:
Create Date: 2026-08-14 15:06:09.933662

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a19bbba74005"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "contracts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
            comment="ID платежа",
        ),
        sa.Column("file_hash", sa.String(), nullable=False, comment="Хеш содержимого файла"),
        sa.Column("file_name", sa.String(), nullable=False, comment="Имя файла"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="Время создания",
        ),
        sa.Column("amount", sa.DECIMAL(18, 2), nullable=True, comment="Сумма"),
        sa.Column("start_date", sa.Date(), nullable=True, comment="Дата начала работ"),
        sa.Column("end_date", sa.Date(), nullable=True, comment="Дата окончания работ"),
        sa.Column(
            "requirements",
            postgresql.JSONB(none_as_null=True),
            nullable=True,
            server_default=sa.text("'[]'"),
            comment="Ключевые требования к исполнителю",
        ),
        sa.Column(
            "penalties",
            postgresql.JSONB(none_as_null=True),
            nullable=True,
            server_default=sa.text("'[]'"),
            comment="Список штрафов",
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True, comment="Время обработки"),
        sa.Column("processing_error_message", sa.String(), nullable=True, comment="Сообщение об ошибке обработки"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contracts")),
        comment="Список контрактов",
    )

    op.create_index(
        op.f("uq_contracts_file_hash"),
        "contracts",
        ["file_hash"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("contracts")
