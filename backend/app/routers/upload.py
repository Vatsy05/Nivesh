"""
Upload router — PDF upload to Supabase Storage → parse → match → store.
"""
import uuid
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import UploadedDocument, Portfolio
from app.schemas import UploadResponse
from app.config import settings
from parser.cam_cas_parser import parse_pdf
from matcher.fund_matcher import match_scheme_code
from services.encryption import encrypt_data

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Upload"])


def _get_user_id(x_user_id: str = Header(...)) -> str:
    """Extract user_id from the X-User-Id header set by Next.js proxy."""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    return x_user_id


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    user_id: str = Depends(_get_user_id),
    db: Session = Depends(get_db),
):
    """
    Upload a PDF statement:
    1. Validate PDF type
    2. Upload encrypted file to Supabase Storage
    3. Parse transactions from PDF
    4. Match fund names via mfapi.in
    5. Store transactions in portfolios table
    """
    # ── Validate ──────────────────────────────────────────────────────────
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    pdf_bytes = await file.read()
    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # ── Upload to Supabase Storage ────────────────────────────────────────
    doc_id = uuid.uuid4()
    storage_path = f"{user_id}/{doc_id}.enc"

    try:
        encrypted = encrypt_data(pdf_bytes)
        # Store via Supabase client
        try:
            from supabase import create_client
            sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
            sb.storage.from_("cam-cas-uploads").upload(
                storage_path,
                encrypted,
                file_options={"content-type": "application/octet-stream"}
            )
        except Exception as e:
            logger.error(f"Supabase Storage upload failed: {e}")
            # Fall through — parse anyway, storage is non-blocking
    except Exception as e:
        logger.error(f"Encryption/upload failed: {e}")

    # ── Create document record ────────────────────────────────────────────
    document = UploadedDocument(
        id=doc_id,
        user_id=user_id,
        original_filename=file.filename,
        storage_path=storage_path,
        parse_status="pending",
    )
    db.add(document)
    db.flush()

    # ── Parse PDF ─────────────────────────────────────────────────────────
    parse_status = "pending"
    transactions_data = []

    try:
        result = parse_pdf(pdf_bytes)

        if not result["transactions"]:
            parse_status = "failed"
        elif len(result["transactions"]) < 3:
            parse_status = "partial"
        else:
            parse_status = "success"

        for err in result.get("errors", []):
            logger.error(f"Parse error in {file.filename}: {err}")

        # ── Match fund names via mfapi.in ─────────────────────────────────
        scheme_map = {}
        for fund_name in result.get("fund_names", []):
            if fund_name not in scheme_map:
                try:
                    code = await match_scheme_code(fund_name)
                    scheme_map[fund_name] = code
                except Exception as e:
                    logger.error(f"mfapi.in match failed for '{fund_name}': {e}")
                    scheme_map[fund_name] = None

        # ── Store transactions ────────────────────────────────────────────
        for txn in result["transactions"]:
            scheme_code = scheme_map.get(txn.get("fund_name"))
            match_status = "matched" if scheme_code else "unmatched"

            portfolio = Portfolio(
                user_id=user_id,
                document_id=doc_id,
                fund_name=txn.get("fund_name", "Unknown Fund"),
                scheme_code=scheme_code,
                folio_number=txn.get("folio_number"),
                account_holder_name=txn.get("account_holder_name"),
                transaction_type=txn.get("transaction_type", "lumpsum"),
                transaction_date=txn.get("transaction_date"),
                amount_inr=txn.get("amount_inr"),
                units=txn.get("units"),
                nav_at_transaction=txn.get("nav_at_transaction"),
                scheme_match_status=match_status,
            )
            db.add(portfolio)
            transactions_data.append(txn)

    except Exception as e:
        parse_status = "failed"
        logger.error(f"Parse pipeline failed: {e}")

    document.parse_status = parse_status
    db.commit()

    fund_names = list(set(t.get("fund_name", "") for t in transactions_data))

    return UploadResponse(
        document_id=str(doc_id),
        parse_status=parse_status,
        transactions_extracted=len(transactions_data),
        funds_found=fund_names,
    )
