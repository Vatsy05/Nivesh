"""
Pydantic schemas for request/response validation.
"""
import uuid
from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ── Upload ────────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    document_id: str
    parse_status: str
    transactions_extracted: int
    funds_found: List[str]


# ── Portfolio ─────────────────────────────────────────────────────────────────

class TransactionBase(BaseModel):
    fund_name: str
    scheme_code: Optional[str] = None
    folio_number: Optional[str] = None
    account_holder_name: Optional[str] = None
    transaction_type: str
    transaction_date: date
    amount_inr: Optional[float] = None
    units: Optional[float] = None
    nav_at_transaction: Optional[float] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    fund_name: Optional[str] = None
    scheme_code: Optional[str] = None
    folio_number: Optional[str] = None
    account_holder_name: Optional[str] = None
    transaction_type: Optional[str] = None
    transaction_date: Optional[date] = None
    amount_inr: Optional[float] = None
    units: Optional[float] = None
    nav_at_transaction: Optional[float] = None


class TransactionResponse(TransactionBase):
    id: str
    document_id: Optional[str] = None
    current_units: Optional[float] = None
    scheme_match_status: str = "matched"
    created_at: datetime

    class Config:
        from_attributes = True


class PortfolioResponse(BaseModel):
    transactions: List[TransactionResponse]
    total_count: int
