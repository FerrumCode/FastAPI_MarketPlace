import uuid
from datetime import datetime
from typing import Annotated

from sqlalchemy import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, mapped_column


uuidpk = Annotated[
    uuid.UUID,
    mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
]

created_ts = Annotated[
    datetime,
    mapped_column(TIMESTAMP, default=datetime.utcnow)
]
