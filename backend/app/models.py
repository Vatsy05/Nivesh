"""
SQLAlchemy ORM models matching the Supabase PostgreSQL schema.
"""
import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import Column, String, Text, Numeric, Date, DateTime, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, unique=True, nullable=False)
    hashed_password = Column(Text, nullable=False)
    name = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    documents = relationship("UploadedDocument", back_populates="user", cascade="all, delete-orphan")
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")


class UploadedDocument(Base):
    __tablename__ = "uploaded_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    original_filename = Column(Text, nullable=False)
    storage_path = Column(Text, nullable=False)
    upload_time = Column(DateTime, default=datetime.utcnow)
    parse_status = Column(Text, default="pending")

    user = relationship("User", back_populates="documents")
    portfolios = relationship("Portfolio", back_populates="document")


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("uploaded_documents.id", ondelete="SET NULL"), nullable=True)
    fund_name = Column(Text, nullable=False)
    scheme_code = Column(Text, nullable=True)
    folio_number = Column(Text, nullable=True)
    account_holder_name = Column(Text, nullable=True)
    transaction_type = Column(Text, nullable=False)
    transaction_date = Column(Date, nullable=False)
    amount_inr = Column(Numeric(14, 2), nullable=True)
    units = Column(Numeric(14, 6), nullable=True)
    nav_at_transaction = Column(Numeric(10, 4), nullable=True)
    current_units = Column(Numeric(14, 6), nullable=True)
    scheme_match_status = Column(Text, default="matched")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="portfolios")
    document = relationship("UploadedDocument", back_populates="portfolios")


class NavCache(Base):
    __tablename__ = "nav_cache"

    scheme_code = Column(Text, primary_key=True)
    current_nav = Column(Numeric(10, 4), nullable=True)
    last_refreshed = Column(DateTime, nullable=True)
