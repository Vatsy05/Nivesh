"""
Upload router — PDF upload to Supabase Storage → parse → match → store.
"""
import asyncio
import uuid
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header
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
    password: str = Form(default=""),
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
    logger.info(f"/upload: handler entered for user={user_id} filename={file.filename}")

    # ── Validate ──────────────────────────────────────────────────────────
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    pdf_bytes = await file.read()
    logger.info(f"/upload: read {len(pdf_bytes)} bytes from multipart body")
    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # ── Upload to Supabase Storage ────────────────────────────────────────
    # The supabase-py client is SYNCHRONOUS — calling it directly blocks the
    # asyncio event loop, and if Supabase is misconfigured or slow it can
    # stall the entire request before we even reach the parser. We run it in
    # a thread and cap it with a 10 s timeout; storage is non-essential
    # (parsing still works without it).
    doc_id = uuid.uuid4()
    storage_path = f"{user_id}/{doc_id}.enc"

    def _sync_upload_to_supabase(path: str, payload: bytes) -> None:
        from supabase import create_client
        sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        sb.storage.from_("cam-cas-uploads").upload(
            path,
            payload,
            file_options={"content-type": "application/octet-stream"},
        )

    try:
        encrypted = encrypt_data(pdf_bytes)
        try:
            await asyncio.wait_for(
                asyncio.to_thread(_sync_upload_to_supabase, storage_path, encrypted),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            logger.warning("Supabase Storage upload timed out after 10s — continuing without it")
        except Exception as e:
            logger.error(f"Supabase Storage upload failed: {e}")
            # Storage is non-blocking — fall through and parse anyway
    except Exception as e:
        logger.error(f"Encryption failed: {e}")

    # ── Clear ALL previous data for this user (prevent accumulation) ──────
    # We must delete ALL portfolio rows, not just those linked to a document_id,
    # because ON DELETE SET NULL causes old rows to become orphans with
    # document_id = NULL which the old logic never cleared.
    # synchronize_session=False skips the SELECT-then-DELETE roundtrip that
    # "fetch" does — much faster on Supabase + PgBouncer.
    logger.info(f"/upload: clearing previous portfolio rows for user={user_id}")
    try:
        deleted_portfolio = db.query(Portfolio).filter(
            Portfolio.user_id == user_id
        ).delete(synchronize_session=False)

        deleted_docs = db.query(UploadedDocument).filter(
            UploadedDocument.user_id == user_id
        ).delete(synchronize_session=False)

        db.flush()
        logger.info(
            f"/upload: cleared {deleted_portfolio} portfolio rows and "
            f"{deleted_docs} documents for user {user_id}"
        )
    except Exception as e:
        logger.warning(f"Could not clear previous records: {e}")
        db.rollback()

    # NOTE: portfolio_snapshots is invalidated lazily — the /holdings/history
    # endpoint detects that snapshots are stale (latest snapshot < latest txn)
    # and rebuilds automatically. This avoids blocking the upload on a table
    # that may not exist yet (pre-migration_module3.sql).


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
        logger.info(f"Starting PDF parse for user {user_id}, file: {file.filename}")

        # Add timeout to prevent hanging on password-protected PDFs
        # If password is wrong or encryption is slow, timeout after 30 seconds
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(parse_pdf, pdf_bytes, password),
                timeout=30.0
            )
            logger.info(f"PDF parse complete: {len(result.get('transactions', []))} transactions extracted")
        except asyncio.TimeoutError:
            logger.error(f"PDF parsing timeout after 30s — likely password issue")
            raise HTTPException(
                status_code=400,
                detail="PDF parsing timeout. Check if password is correct or try without password."
            )

        if not result["transactions"]:
            parse_status = "failed"
        elif len(result["transactions"]) < 3:
            parse_status = "partial"
        else:
            parse_status = "success"

        for err in result.get("errors", []):
            logger.error(f"Parse error in {file.filename}: {err}")

        # ── Match fund names via mfapi.in (CONCURRENT) ───────────────────────
        scheme_map: dict = {}
        scheme_name_map = result.get("scheme_name_map", {})
        fund_names_list = result.get("fund_names", [])

        async def _match_one(fund_name: str):
            sname = scheme_name_map.get(fund_name, "")
            try:
                # Add 10-second timeout per fund to prevent hangs
                code = await asyncio.wait_for(
                    match_scheme_code(fund_name, scheme_name=sname),
                    timeout=10.0
                )
                logger.info(f"Matched '{fund_name}' → scheme_code={code}")
                return fund_name, code
            except asyncio.TimeoutError:
                logger.warning(f"mfapi.in match TIMEOUT for '{fund_name}' (10s)")
                return fund_name, None
            except Exception as e:
                logger.error(f"mfapi.in match failed for '{fund_name}': {e}")
                return fund_name, None

        logger.info(f"Starting concurrent fund matching for {len(fund_names_list)} funds...")
        try:
            # Overall timeout: 60 seconds for all funds, or 10 seconds per fund minimum
            matched = await asyncio.wait_for(
                asyncio.gather(*[_match_one(fn) for fn in fund_names_list]),
                timeout=max(60.0, len(fund_names_list) * 3.0)
            )
        except asyncio.TimeoutError:
            logger.warning(f"Overall fund matching timeout — continuing with partial results")
            matched = [(fn, None) for fn in fund_names_list]

        scheme_map = dict(matched)
        matched_count = sum(1 for _, code in matched if code is not None)
        logger.info(f"Fund matching complete: {matched_count}/{len(fund_names_list)} matched")

        # ── Store transactions ────────────────────────────────────────────
        logger.info(f"Storing {len(result['transactions'])} transactions to database...")
        closing_balances = result.get("closing_balances", {})
        funds_with_transactions: set = set()

        # For each fund, find the earliest in-window transaction's date + NAV.
        # We use these to build a synthetic "opening balance" purchase so that
        # XIRR has a sane starting position for units the user already held
        # before the statement period (without which XIRR explodes to >100x).
        first_txn_meta: dict = {}  # fund_name -> {"date": d, "nav": n}
        for txn in result["transactions"]:
            fn = txn.get("fund_name", "Unknown Fund")
            d = txn.get("transaction_date")
            nav = txn.get("nav_at_transaction")
            if not d or not nav:
                continue
            cur = first_txn_meta.get(fn)
            if cur is None or d < cur["date"]:
                first_txn_meta[fn] = {"date": d, "nav": float(nav)}

        for idx, txn in enumerate(result["transactions"]):
            fund_name = txn.get("fund_name", "Unknown Fund")
            scheme_code = scheme_map.get(fund_name)
            match_status = "matched" if scheme_code else "unmatched"
            funds_with_transactions.add(fund_name)

            # Stamp the PDF's closing-balance units on every row of this fund.
            # The reconstructor reads current_units to decide whether a fund
            # is fully redeemed; without this, funds that are net-redeemed
            # in the statement period (purchases < redemptions) get treated
            # as fully redeemed even when the PDF clearly shows residual
            # units carried over from before the statement window.
            fund_close = closing_balances.get(fund_name) or {}
            row_current_units = fund_close.get("closing_units")

            portfolio = Portfolio(
                user_id=user_id,
                document_id=doc_id,
                fund_name=fund_name,
                scheme_code=scheme_code,
                folio_number=txn.get("folio_number"),
                account_holder_name=txn.get("account_holder_name"),
                transaction_type=txn.get("transaction_type", "lumpsum"),
                transaction_date=txn.get("transaction_date"),
                amount_inr=txn.get("amount_inr"),
                units=txn.get("units"),
                nav_at_transaction=txn.get("nav_at_transaction"),
                current_units=row_current_units,
                scheme_match_status=match_status,
            )
            db.add(portfolio)
            transactions_data.append(txn)

        # ── Synthetic "opening balance" purchases ─────────────────────────
        # For each fund whose PDF shows Opening Unit Balance > 0, add a
        # synthetic purchase at the statement period START (or one day before
        # the first in-window transaction if the period header wasn't parsed),
        # priced at that fund's first in-window NAV. This gives XIRR a
        # realistic starting cashflow and stops it from interpreting
        # redemptions as a 100x return on the in-window SIPs.
        from datetime import date as _date, timedelta as _td
        statement_start = result.get("statement_start")
        for fund_name, bal in closing_balances.items():
            opening_units = bal.get("opening_units")
            if not opening_units or opening_units <= 0:
                continue
            meta = first_txn_meta.get(fund_name)
            if not meta:
                continue
            # Prefer the statement-period start so opening units sit at the
            # correct point on the timeline. Fall back to the day before the
            # first in-window transaction if the period header isn't known.
            if statement_start and statement_start <= meta["date"]:
                synth_date = statement_start
            else:
                synth_date = meta["date"] - _td(days=1)
            synth_nav = meta["nav"]
            synth_amount = round(opening_units * synth_nav, 2)
            scheme_code = scheme_map.get(fund_name)
            match_status = "matched" if scheme_code else "unmatched"
            fund_close = closing_balances.get(fund_name) or {}
            row_current_units = fund_close.get("closing_units")

            opening_row = Portfolio(
                user_id=user_id,
                document_id=doc_id,
                fund_name=fund_name,
                scheme_code=scheme_code,
                transaction_type="lumpsum",
                transaction_date=synth_date,
                amount_inr=synth_amount,
                units=opening_units,
                nav_at_transaction=synth_nav,
                current_units=row_current_units,
                scheme_match_status=match_status,
                account_holder_name=result.get("account_holder_name", ""),
            )
            db.add(opening_row)
            logger.info(
                f"Opening balance synthetic for '{fund_name}': "
                f"{opening_units} units @ NAV {synth_nav} on {synth_date} "
                f"= ₹{synth_amount}"
            )

        # ── Synthetic holdings for funds with closing balance but no txns ──
        # current_units is already written on every row by the loop above.
        # Here we only need to handle funds that appear in the PDF's closing
        # balances but have NO transactions in this statement period (e.g.
        # bought before the statement window and untouched during it).
        statement_date = _date.today()

        logger.info(f"Processing {len(closing_balances)} closing balances...")
        for fund_name, bal in closing_balances.items():
            closing_units = bal.get("closing_units")
            market_value = bal.get("market_value")
            closing_nav = bal.get("closing_nav")

            if closing_units is None:
                continue

            scheme_code = scheme_map.get(fund_name)

            # If this fund has NO transactions in the PDF but appears in
            # closing balances, it means the user holds it from a prior period.
            # Create a synthetic holding row so analytics can see it.
            if fund_name not in funds_with_transactions and closing_units > 0:
                match_status = "matched" if scheme_code else "unmatched"
                synthetic_nav = (market_value / closing_units) if (market_value and closing_units > 0) else closing_nav

                holding_row = Portfolio(
                    user_id=user_id,
                    document_id=doc_id,
                    fund_name=fund_name,
                    scheme_code=scheme_code,
                    transaction_type="lumpsum",   # placeholder — not a real txn
                    transaction_date=statement_date,
                    amount_inr=market_value or 0.0,
                    units=closing_units,
                    nav_at_transaction=synthetic_nav,
                    current_units=closing_units,
                    scheme_match_status=match_status,
                    account_holder_name=result.get("account_holder_name", ""),
                )
                db.add(holding_row)
                logger.info(
                    f"Created synthetic holding row for '{fund_name}': "
                    f"{closing_units} units, market_value={market_value}"
                )

    except Exception as e:
        parse_status = "failed"
        logger.error(f"Parse pipeline failed: {e}")

    document.parse_status = parse_status
    logger.info(f"Committing {len(transactions_data)} transactions to database...")
    try:
        db.commit()
        logger.info(f"Database commit successful. Parse status: {parse_status}")
    except Exception as e:
        logger.error(f"Database commit failed: {e}")
        db.rollback()
        parse_status = "failed"
        raise

    fund_names = list(set(t.get("fund_name", "") for t in transactions_data))

    return UploadResponse(
        document_id=str(doc_id),
        parse_status=parse_status,
        transactions_extracted=len(transactions_data),
        funds_found=fund_names,
    )

