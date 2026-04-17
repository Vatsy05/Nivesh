"""
Portfolio router — CRUD + NAV refresh with 4-hour caching.
"""
import uuid
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Portfolio, NavCache
from app.schemas import (
    TransactionCreate, TransactionUpdate, TransactionResponse, PortfolioResponse
)
from matcher.fund_matcher import match_scheme_code, get_latest_nav

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Portfolio"])

CACHE_HOURS = 4


def _get_user_id(x_user_id: str = Header(...)) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    return x_user_id


def _to_response(txn: Portfolio) -> TransactionResponse:
    return TransactionResponse(
        id=str(txn.id),
        document_id=str(txn.document_id) if txn.document_id else None,
        fund_name=txn.fund_name,
        scheme_code=txn.scheme_code,
        folio_number=txn.folio_number,
        account_holder_name=txn.account_holder_name,
        transaction_type=txn.transaction_type,
        transaction_date=txn.transaction_date,
        amount_inr=float(txn.amount_inr) if txn.amount_inr else None,
        units=float(txn.units) if txn.units else None,
        nav_at_transaction=float(txn.nav_at_transaction) if txn.nav_at_transaction else None,
        current_units=float(txn.current_units) if txn.current_units else None,
        scheme_match_status=txn.scheme_match_status or "matched",
        created_at=txn.created_at,
    )


@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio(
    user_id: str = Depends(_get_user_id),
    db: Session = Depends(get_db),
):
    """
    Get all portfolio transactions. Refreshes current_units from mfapi.in
    with 4-hour cache per scheme_code.
    """
    # Refresh NAV + current_units
    await _refresh_units(db, user_id)

    transactions = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == user_id)
        .order_by(Portfolio.transaction_date.desc())
        .all()
    )

    return PortfolioResponse(
        transactions=[_to_response(t) for t in transactions],
        total_count=len(transactions),
    )


@router.post("/portfolio/manual", response_model=TransactionResponse, status_code=201)
async def add_manual_transaction(
    data: TransactionCreate,
    user_id: str = Depends(_get_user_id),
    db: Session = Depends(get_db),
):
    """Manually add a single transaction."""
    valid_types = {"SIP", "lumpsum", "redemption", "switch_in", "switch_out"}
    if data.transaction_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid type. Must be one of: {valid_types}")

    # Look up scheme code
    scheme_code = None
    match_status = "manual"
    try:
        scheme_code = await match_scheme_code(data.fund_name)
        if scheme_code:
            match_status = "matched"
        else:
            match_status = "unmatched"
    except Exception as e:
        logger.error(f"Scheme lookup failed: {e}")

    txn = Portfolio(
        user_id=user_id,
        fund_name=data.fund_name,
        scheme_code=scheme_code,
        folio_number=data.folio_number,
        account_holder_name=data.account_holder_name,
        transaction_type=data.transaction_type,
        transaction_date=data.transaction_date,
        amount_inr=data.amount_inr,
        units=data.units,
        nav_at_transaction=data.nav_at_transaction,
        scheme_match_status=match_status,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return _to_response(txn)


@router.patch("/portfolio/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: str,
    data: TransactionUpdate,
    user_id: str = Depends(_get_user_id),
    db: Session = Depends(get_db),
):
    """Update a transaction. Re-runs scheme matching if fund_name changed."""
    txn = db.query(Portfolio).filter(
        Portfolio.id == transaction_id,
        Portfolio.user_id == user_id,
    ).first()

    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    update_dict = data.model_dump(exclude_unset=True)

    # Re-match scheme code if fund_name changed
    if "fund_name" in update_dict and update_dict["fund_name"]:
        try:
            new_code = await match_scheme_code(update_dict["fund_name"])
            update_dict["scheme_code"] = new_code
            update_dict["scheme_match_status"] = "matched" if new_code else "unmatched"
        except Exception:
            update_dict["scheme_match_status"] = "unmatched"

    for key, val in update_dict.items():
        if val is not None:
            setattr(txn, key, val)

    db.commit()
    db.refresh(txn)
    return _to_response(txn)


@router.delete("/portfolio/{transaction_id}")
async def delete_transaction(
    transaction_id: str,
    user_id: str = Depends(_get_user_id),
    db: Session = Depends(get_db),
):
    """Delete a transaction (ownership verified)."""
    txn = db.query(Portfolio).filter(
        Portfolio.id == transaction_id,
        Portfolio.user_id == user_id,
    ).first()

    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(txn)
    db.commit()
    return {"message": "Transaction deleted"}


async def _refresh_units(db: Session, user_id: str) -> None:
    """
    For each unique scheme_code:
    1. Check nav_cache — skip if refreshed < 4 hours ago
    2. Fetch latest NAV from mfapi.in and update cache
    3. Calculate net units (purchases - redemptions)
    4. Update current_units on all portfolio rows
    """
    scheme_codes = (
        db.query(Portfolio.scheme_code)
        .filter(Portfolio.user_id == user_id, Portfolio.scheme_code.isnot(None))
        .distinct()
        .all()
    )

    purchase_types = {"SIP", "lumpsum", "switch_in"}
    redemption_types = {"redemption", "switch_out"}

    for (scheme_code,) in scheme_codes:
        # Check cache
        cached = db.query(NavCache).filter(NavCache.scheme_code == scheme_code).first()
        if cached and cached.last_refreshed:
            if datetime.utcnow() - cached.last_refreshed < timedelta(hours=CACHE_HOURS):
                # Still update current_units from existing data
                _update_net_units(db, user_id, scheme_code, purchase_types, redemption_types)
                continue

        # Fetch NAV
        try:
            nav = await get_latest_nav(scheme_code)
            if nav is not None:
                if cached:
                    cached.current_nav = nav
                    cached.last_refreshed = datetime.utcnow()
                else:
                    db.add(NavCache(scheme_code=scheme_code, current_nav=nav, last_refreshed=datetime.utcnow()))
                db.flush()
        except Exception as e:
            logger.error(f"NAV refresh failed for {scheme_code}: {e}")

        _update_net_units(db, user_id, scheme_code, purchase_types, redemption_types)

    db.commit()


def _update_net_units(db: Session, user_id: str, scheme_code: str, purchase_types: set, redemption_types: set):
    """Calculate net units for a scheme and update all rows."""
    purchased = db.query(func.coalesce(func.sum(Portfolio.units), 0)).filter(
        Portfolio.user_id == user_id,
        Portfolio.scheme_code == scheme_code,
        Portfolio.transaction_type.in_(purchase_types),
    ).scalar()

    redeemed = db.query(func.coalesce(func.sum(Portfolio.units), 0)).filter(
        Portfolio.user_id == user_id,
        Portfolio.scheme_code == scheme_code,
        Portfolio.transaction_type.in_(redemption_types),
    ).scalar()

    net = max(float(purchased) - float(redeemed), 0)

    db.query(Portfolio).filter(
        Portfolio.user_id == user_id,
        Portfolio.scheme_code == scheme_code,
    ).update({"current_units": net}, synchronize_session="fetch")
