"""
Analytics router — Module 2 Returns & Performance Analytics.

All endpoints are read-only (GET) and require X-User-Id authentication
using the same pattern as portfolio.py.

Endpoints:
  GET /analytics/summary        — portfolio + per-fund XIRR/CAGR/returns
  GET /analytics/growth         — portfolio growth time series
  GET /analytics/rolling        — rolling return series for a scheme
  GET /analytics/p2p            — point-to-point return
  GET /analytics/events         — static market event annotations
"""
import logging
from datetime import date
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Portfolio
from analytics.portfolio_aggregator import (
    get_fund_summary_rows,
    get_portfolio_cashflows,
    get_total_portfolio_value,
    get_total_invested,
    get_portfolio_growth_series,
    get_fund_invested_amounts,
    get_fund_current_values,
)
from analytics.xirr_engine import compute_xirr, compute_cagr, compute_absolute_return, compute_all_metrics
from analytics.rolling_returns import fetch_historical_nav, compute_rolling_summary, compute_rolling_series_all_windows, compute_p2p_return
from analytics.market_events import MARKET_EVENTS, get_events_in_range

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _get_user_id(x_user_id: str = Header(...)) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    return x_user_id


# ── Pydantic response schemas ──────────────────────────────────────────────────

class FundMetrics(BaseModel):
    fund_name: str
    scheme_code: Optional[str]
    invested: float
    current_value: float
    gain_loss: float
    xirr_pct: Optional[float]
    cagr_pct: Optional[float]
    absolute_return_pct: Optional[float]
    first_investment_date: Optional[date]


class PortfolioSummaryResponse(BaseModel):
    total_invested: float
    total_current_value: float
    total_gain_loss: float
    portfolio_xirr_pct: Optional[float]
    portfolio_cagr_pct: Optional[float]
    portfolio_absolute_return_pct: Optional[float]
    funds: List[FundMetrics]
    as_of: date


class GrowthPoint(BaseModel):
    date: str
    invested_amount: float
    current_value: float


class GrowthResponse(BaseModel):
    series: List[GrowthPoint]
    total_points: int


class RollingWindowSummary(BaseModel):
    min: Optional[float]
    max: Optional[float]
    median: Optional[float]
    current: Optional[float]


class RollingPoint(BaseModel):
    date: str
    return_pct: float


class RollingResponse(BaseModel):
    scheme_code: str
    summary: Dict[str, Optional[RollingWindowSummary]]
    series: Dict[str, List[RollingPoint]]


class P2PResponse(BaseModel):
    scheme_code: str
    start_date: date
    end_date: date
    return_pct: Optional[float]
    message: Optional[str]


class MarketEvent(BaseModel):
    date: str
    label: str
    short_label: str
    type: str
    description: str


class EventsResponse(BaseModel):
    events: List[MarketEvent]


# ── /analytics/summary ─────────────────────────────────────────────────────────

@router.get("/summary", response_model=PortfolioSummaryResponse)
async def get_analytics_summary(
    user_id: str = Depends(_get_user_id),
    db: Session = Depends(get_db),
):
    """
    Compute XIRR, CAGR, and absolute return for the entire portfolio
    and each individual fund.
    """
    today = date.today()
    fund_rows = get_fund_summary_rows(db, user_id)

    if not fund_rows:
        return PortfolioSummaryResponse(
            total_invested=0,
            total_current_value=0,
            total_gain_loss=0,
            portfolio_xirr_pct=None,
            portfolio_cagr_pct=None,
            portfolio_absolute_return_pct=None,
            funds=[],
            as_of=today,
        )

    # Portfolio-level
    portfolio_cashflows = get_portfolio_cashflows(db, user_id)
    total_invested = get_total_invested(db, user_id)
    total_current = get_total_portfolio_value(db, user_id)

    port_metrics = compute_all_metrics(
        cashflows=portfolio_cashflows,
        invested_amount=total_invested,
        current_value=total_current,
    )

    # Per-fund
    fund_metrics_list: List[FundMetrics] = []
    for row in fund_rows:
        m = compute_all_metrics(
            cashflows=row["cashflows"],
            invested_amount=row["invested"],
            current_value=row["current_value"],
            first_date=row["first_date"],
        )
        fund_metrics_list.append(FundMetrics(
            fund_name=row["fund_name"],
            scheme_code=row["scheme_code"],
            invested=row["invested"],
            current_value=row["current_value"],
            gain_loss=round(row["current_value"] - row["invested"], 2),
            xirr_pct=m["xirr_pct"],
            cagr_pct=m["cagr_pct"],
            absolute_return_pct=m["absolute_return_pct"],
            first_investment_date=row["first_date"],
        ))

    # Sort funds by XIRR descending (None last)
    fund_metrics_list.sort(
        key=lambda f: f.xirr_pct if f.xirr_pct is not None else float("-inf"),
        reverse=True,
    )

    return PortfolioSummaryResponse(
        total_invested=round(total_invested, 2),
        total_current_value=round(total_current, 2),
        total_gain_loss=round(total_current - total_invested, 2),
        portfolio_xirr_pct=port_metrics["xirr_pct"],
        portfolio_cagr_pct=port_metrics["cagr_pct"],
        portfolio_absolute_return_pct=port_metrics["absolute_return_pct"],
        funds=fund_metrics_list,
        as_of=today,
    )


# ── /analytics/growth ──────────────────────────────────────────────────────────

@router.get("/growth", response_model=GrowthResponse)
async def get_portfolio_growth(
    user_id: str = Depends(_get_user_id),
    db: Session = Depends(get_db),
):
    """
    Return portfolio growth time series: invested amount vs current value over time.
    """
    series = get_portfolio_growth_series(db, user_id)

    if not series:
        return GrowthResponse(series=[], total_points=0)

    return GrowthResponse(
        series=[GrowthPoint(**p) for p in series],
        total_points=len(series),
    )


# ── /analytics/rolling ─────────────────────────────────────────────────────────

@router.get("/rolling", response_model=RollingResponse)
async def get_rolling_returns(
    scheme_code: str = Query(..., description="AMFI scheme code"),
    user_id: str = Depends(_get_user_id),
    db: Session = Depends(get_db),
):
    """
    Fetch historical NAV and compute 1Y/3Y/5Y rolling return series + summary.
    Results are cached in historical_nav_cache (24h TTL).
    """
    # Verify user has this scheme_code in their portfolio
    owns = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == user_id, Portfolio.scheme_code == scheme_code)
        .first()
    )
    if not owns:
        raise HTTPException(status_code=404, detail=f"Scheme {scheme_code} not found in your portfolio")

    nav_df = await fetch_historical_nav(scheme_code, db)

    if nav_df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No historical NAV data available for scheme {scheme_code}",
        )

    raw_summary = compute_rolling_summary(nav_df)
    summary: Dict[str, Optional[RollingWindowSummary]] = {}
    for window, val in raw_summary.items():
        if val is None:
            summary[window] = None
        else:
            summary[window] = RollingWindowSummary(**val)

    raw_series = compute_rolling_series_all_windows(nav_df)
    series: Dict[str, List[RollingPoint]] = {}
    for window, pts in raw_series.items():
        series[window] = [RollingPoint(**p) for p in pts]

    return RollingResponse(
        scheme_code=scheme_code,
        summary=summary,
        series=series,
    )


# ── /analytics/p2p ────────────────────────────────────────────────────────────

@router.get("/p2p", response_model=P2PResponse)
async def get_p2p_return(
    scheme_code: str = Query(..., description="AMFI scheme code"),
    start: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: date = Query(..., description="End date (YYYY-MM-DD)"),
    user_id: str = Depends(_get_user_id),
    db: Session = Depends(get_db),
):
    """
    Compute point-to-point return for a scheme between two dates.
    """
    if start >= end:
        raise HTTPException(status_code=400, detail="start must be before end")

    # Verify ownership
    owns = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == user_id, Portfolio.scheme_code == scheme_code)
        .first()
    )
    if not owns:
        raise HTTPException(status_code=404, detail=f"Scheme {scheme_code} not found in your portfolio")

    nav_df = await fetch_historical_nav(scheme_code, db)
    if nav_df.empty:
        return P2PResponse(
            scheme_code=scheme_code,
            start_date=start,
            end_date=end,
            return_pct=None,
            message="No historical NAV data available for this scheme",
        )

    ret = compute_p2p_return(nav_df, start, end)
    return P2PResponse(
        scheme_code=scheme_code,
        start_date=start,
        end_date=end,
        return_pct=ret,
        message=None if ret is not None else "Could not compute return — NAV data unavailable for selected dates",
    )


# ── /analytics/events ─────────────────────────────────────────────────────────

@router.get("/events", response_model=EventsResponse)
async def get_market_events(
    start: Optional[str] = Query(None, description="Filter start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="Filter end date YYYY-MM-DD"),
    user_id: str = Depends(_get_user_id),
):
    """
    Return static Indian market event annotations for chart overlays.
    Optionally filter by date range.
    """
    if start and end:
        events = get_events_in_range(start, end)
    else:
        events = MARKET_EVENTS

    return EventsResponse(events=[MarketEvent(**e) for e in events])


# ── /analytics/debug ──────────────────────────────────────────────────────────

@router.get("/debug")
async def debug_portfolio(
    user_id: str = Depends(_get_user_id),
    db: Session = Depends(get_db),
):
    """
    Diagnostic endpoint: returns raw transaction counts, invested totals per fund,
    unmatched funds, and duplicate detection.  Use this to diagnose data issues.
    """
    from sqlalchemy import func as sqlfunc

    # Count transactions per fund per type
    rows = (
        db.query(
            Portfolio.fund_name,
            Portfolio.transaction_type,
            Portfolio.scheme_code,
            sqlfunc.count(Portfolio.id).label("count"),
            sqlfunc.sum(Portfolio.amount_inr).label("total_amount"),
        )
        .filter(Portfolio.user_id == user_id)
        .group_by(Portfolio.fund_name, Portfolio.transaction_type, Portfolio.scheme_code)
        .all()
    )

    breakdown = []
    for fund_name, txn_type, scheme_code, count, total in rows:
        breakdown.append({
            "fund_name": fund_name,
            "transaction_type": txn_type,
            "scheme_code": scheme_code,
            "count": count,
            "total_amount_inr": float(total) if total else 0,
        })

    total_invested = get_total_invested(db, user_id)
    total_current = get_total_portfolio_value(db, user_id)

    unmatched = (
        db.query(Portfolio.fund_name)
        .filter(Portfolio.user_id == user_id, Portfolio.scheme_code.is_(None))
        .distinct()
        .all()
    )

    return {
        "total_invested_computed": round(total_invested, 2),
        "total_current_value_computed": round(total_current, 2),
        "unmatched_funds": [r[0] for r in unmatched],
        "transaction_breakdown": breakdown,
    }


# ── /analytics/rematch ────────────────────────────────────────────────────────

@router.post("/rematch")
async def rematch_unmatched_funds(
    user_id: str = Depends(_get_user_id),
    db: Session = Depends(get_db),
):
    """
    Re-run scheme code matching for all unmatched funds in the user's portfolio.
    Useful after a failed upload match, or to fix stale unmatched records.
    """
    from matcher.fund_matcher import match_scheme_code as _match

    # Get distinct unmatched fund names
    unmatched_rows = (
        db.query(Portfolio.fund_name)
        .filter(Portfolio.user_id == user_id, Portfolio.scheme_code.is_(None))
        .distinct()
        .all()
    )

    if not unmatched_rows:
        return {"message": "No unmatched funds found", "results": []}

    results = []
    for (fund_name,) in unmatched_rows:
        try:
            code = await _match(fund_name, scheme_name=fund_name)
            if code:
                # Update all rows for this fund
                updated = (
                    db.query(Portfolio)
                    .filter(
                        Portfolio.user_id == user_id,
                        Portfolio.fund_name == fund_name,
                        Portfolio.scheme_code.is_(None),
                    )
                    .update(
                        {"scheme_code": code, "scheme_match_status": "matched"},
                        synchronize_session="fetch",
                    )
                )
                results.append({"fund": fund_name, "matched": True, "scheme_code": code, "rows_updated": updated})
                logger.info(f"Re-matched '{fund_name}' → {code} ({updated} rows)")
            else:
                results.append({"fund": fund_name, "matched": False, "scheme_code": None})
                logger.warning(f"Re-match failed for '{fund_name}'")
        except Exception as e:
            results.append({"fund": fund_name, "matched": False, "error": str(e)})

    db.commit()
    matched_count = sum(1 for r in results if r["matched"])
    return {
        "message": f"Re-matched {matched_count}/{len(results)} funds",
        "results": results,
    }

