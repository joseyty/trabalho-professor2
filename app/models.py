from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    balance: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)

class Transfer(Base):
    __tablename__ = "transfers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    origin_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    destination_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

Index("ix_transfer_duplicate_check", Transfer.origin_id, Transfer.destination_id, Transfer.value, Transfer.created_at)
