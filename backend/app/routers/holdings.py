"""
Holdings router — Groww-style portfolio dashboard endpoints.

Endpoints:
  GET  /holdings              — current holdings with live valuation (per fund)
  GET  /holdings/summary      — portfolio-level totals + daily gain + XIRR
  GET  /holdings/history      — daily/monthly valuation history for growth chart
  POST /holdings/rebuild      — force recompute snapshots from scratch
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import NavCache, Portfolio
from holdings.reconstructor import reconstruct_holdings, HoldingRecord
from holdings.valuation import attach_valuations, compute_portfolio_summary
from holdings.snapshot_engine import (
    compute_and_store_snapshots,
    clear_snapshots,
)
from analytics.xirr_engine import compute_all_metrics
from analytics.portfolio_aggregator import get_portfolio_cashflows

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/holdings", tags=["Holdings"])


def _get_user_id(x_user_id: str = Header(...)) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    return x_user_id


def _holding_to_dict(h: HoldingRecord) -> Dict[str, Any]:
    """Serialize a HoldingRecord to a JSON-safe dict."""
    return {
        "fund_name":        h.fund_name,
        "scheme_code":      h.scheme_code,
        "folio_number":     h.folio_number,
        "current_units":    round(h.current_units, 4),
        "purchase_units":   round(h.purchase_units, 4),
        "redemption_units": round(h.redemption_units, 4),
        "invested_amount":  round(h.invested_amount, 2),
        "redeemed_amount":  round(h.redeemed_amount, 2),
        "avg_buy_nav":      round(h.avg_buy_nav, 4)    if h.avg_buy_nav    else None,
        "current_nav":      round(h.current_nav, 4)    if h.current_nav    else None,
        "current_value":    round(h.current_value, 2),
        "unrealized_gain":  round(h.unrealized_gain, 2),
        "unrealized_pct":   round(h.unrealized_pct, 2),
        "realized_gain":    round(h.realized_gain, 2),
        "daily_gain":       round(h.daily_gain, 2),
        "daily_gain_pct":   round(h.daily_gain_pct, 4),
        "is_fully_redeemed": h.is_fully_redeemed,
        "first_purchase":   h.first_purchase.isoformat()    if h.first_purchase    else None,
        "last_transaction": h.last_transaction.isoformat() if h.last_transaction  else None,
    }


# ── GET /holdings ─────────────────────────────────────────────────────────────

@router.get("")
async def get_holdings(
    include_redeemed: bool = Query(False, description="Include fully redeemed funds"),
    user_id: str = Depends(_get_user_id),
    db: Session = Depends(get_db),
):
    """
    Return current holdings with live valuation for each fund.
    Sorted by current_value descending (largest position first).
    """
    holdings = reconstruct_holdings(db, user_id)
    holdings = attach_valuations(db, holdings)

    if not include_redeemed:
        holdings = [h for h in holdings if not h.is_fully_redeemed]

    holdings.sort(key=lambda h: h.current_value, reverse=True)

    return {
        "holdings": [_holding_to_dict(h) for h in holdings],
        "count": len(holdings),
    }


# ── GET /holdings/summary ─────────────────────────────────────────────────────

@router.get("/summary")
async def get_holdings_summary(
    user_id: str = Depends(_get_user_id),
    db: Session = Depends(get_db),
):
    """
    Return portfolio-level summary: total value, invested, P&L, daily gain, XIRR, CAGR.
    This is the top-level dashboard metric bar.
    """
    holdings = reconstruct_holdings(db, user_id)
    holdings = attach_valuations(db, holdings)
    summary  = compute_portfolio_summary(holdings)

    # Compute XIRR / CAGR / Absolute return using existing engine
    cashflows = get_portfolio_cashflows(db, user_id)
    total_invested = summary["total_invested"]
    total_current = summary["total_value"]

    xirr_pct = cagr_pct = abs_return_pct = None
    if cashflows and total_current > 0:
        metrics = compute_all_metrics(cashflows, total_invested, total_current)
        xirr_pct       = metrics.get("xirr_pct")
        cagr_pct       = metrics.get("cagr_pct")
        abs_return_pct = metrics.get("abs_return_pct")

    # Fallback abs return from summary
    if abs_return_pct is None:
        abs_return_pct = summary.get("abs_return_pct")

    return {
        **summary,
        "xirr_pct":       xirr_pct,
        "cagr_pct":       cagr_pct,
        "abs_return_pct": abs_return_pct,
    }


# ── GET /holdings/history ─────────────────────────────────────────────────────

@router.get("/history")
async def get_holdings_history(
    rebuild: bool = Query(False, description="Force rebuild snapshots"),
    user_id: str = Depends(_get_user_id),
    db: Session = Depends(get_db),
):
    """
    Return daily/monthly portfolio valuation history for the growth chart.
    First call triggers NAV fetching and snapshot computation (may take 10-30s).
    Subsequent calls return cached data instantly.
    """
    # Ensure NAV history is available for all scheme codes
    scheme_codes = (
        db.query(Portfolio.scheme_code)
        .filter(
            Portfolio.user_id == user_id,
            Portfolio.scheme_code.isnot(None),
        )
        .distinct()
        .all()
    )
    scheme_codes = [r[0] for r in scheme_codes if r[0]]

    # Fetch NAV history for all schemes concurrently (cache from rolling_returns)
    if scheme_codes:
        from analytics.rolling_returns import fetch_historical_nav

        async def _fetch_nav(sc: str):
            try:
                await fetch_historical_nav(sc, db)
            except Exception as e:
                logger.warning(f"NAV history fetch failed for {sc}: {e}")

        await asyncio.gather(*[_fetch_nav(sc) for sc in scheme_codes])

    snapshots = compute_and_store_snapshots(db, user_id, force=rebuild)

    return {
        "history": snapshots,
        "count": len(snapshots),
        "source": "portfolio_snapshots",
    }


# ── POST /holdings/rebuild ────────────────────────────────────────────────────

@router.post("/rebuild")
async def rebuild_holdings(
    user_id: str = Depends(_get_user_id),
    db: Session = Depends(get_db),
):
    """
    Force full recomputation of portfolio snapshots.
    Also invalidates and re-fetches NAV history for all funds.
    """
    clear_snapshots(db, user_id)

    scheme_codes = (
        db.query(Portfolio.scheme_code)
        .filter(
            Portfolio.user_id == user_id,
            Portfolio.scheme_code.isnot(None),
        )
        .distinct()
        .all()
    )
    scheme_codes = [r[0] for r in scheme_codes if r[0]]

    if scheme_codes:
        from analytics.rolling_returns import fetch_historical_nav

        async def _fetch_nav_rebuild(sc: str):
            try:
                await fetch_historical_nav(sc, db)
            except Exception as e:
                logger.warning(f"NAV fetch failed for {sc}: {e}")

        await asyncio.gather(*[_fetch_nav_rebuild(sc) for sc in scheme_codes])

    snapshots = compute_and_store_snapshots(db, user_id, force=True)

    return {
        "message": f"Rebuilt {len(snapshots)} snapshots across {len(scheme_codes)} funds",
        "snapshots": len(snapshots),
        "funds": len(scheme_codes),
    }
