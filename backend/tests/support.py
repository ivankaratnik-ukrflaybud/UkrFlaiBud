from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import EntityMixin


class TechnicalRecord(EntityMixin, Base):
    __tablename__ = "technical_record"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
