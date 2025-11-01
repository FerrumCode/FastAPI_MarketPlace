# app/models/base.py

import uuid
from datetime import datetime
from typing import Annotated

from sqlalchemy import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy.sql import func  # ИЗМЕНЕНО: добавил func для server_default


class Base(DeclarativeBase):
    """
    Общий declarative base для всех моделей.
    db.py и все модели должны импортировать ИМЕННО это Base.
    """
    pass


uuidpk = Annotated[
    uuid.UUID,
    mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
]

created_ts = Annotated[
    datetime,
    mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now()  # ИЗМЕНЕНО: раньше было default=datetime.utcnow (naive)
    )
]
