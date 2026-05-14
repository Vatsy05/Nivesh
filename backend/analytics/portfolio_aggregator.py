"""
Portfolio aggregator — reads the portfolios + nav_cache tables and produces
structured cashflow data needed by the analytics engine.

Key rules (matching Module 1 conventions):
  - Purchase types : SIP, lumpsum, switch_in  → negative cashflows (money out)
  - Redemption types: redemption, switch_out   → positive cashflows (money in)
  - current_units is already maintained by portfolio.py _refresh_units()
  - current_nav comes from nav_cache (refreshed every 4 hours)
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Portfolio, NavCache

logger = logging.getLogger(__name__)

PURCHASE_TYPES = {"SIP", "lumpsum", "switch_in"}
REDEMPTION_TYPES = {"redemption", "switch_out"}


# ── Cashflow builders ──────────────────────────────────────────────────────────

def get_fund_cashflows(
    db: Session,
    user_id: str,
) -> Dict[str, List[Tuple[date, float]]]:
    """
    Return per-fund cashflow lists suitable for XIRR computation.

    Cashflow sign convention (standard finance):
      investments  → negative  (money leaving the investor's pocket)
      redemptions  → positive  (money returning to the investor)

    Returns:
        Dict mapping fund_name → [(date, signed_amount), ...]
        Sorted ascending by date.
    """
    rows = (
        db.query(
            Portfolio.fund_name,
            Portfolio.transaction_date,
            Portfolio.transaction_type,
            Portfolio.amount_inr,
        )
        .filter(
            Portfolio.user_id == user_id,
            Portfolio.amount_inr.isnot(None),
            Portfolio.transaction_date.isnot(None),
        )
        .order_by(Portfolio.transaction_date.asc())
        .all()
    )

    fund_map: Dict[str, List[Tuple[date, float]]] = defaultdict(list)
    for fund_name, txn_date, txn_type, amount in rows:
        amt = float(amount)
        if txn_type in PURCHASE_TYPES:
            signed = -abs(amt)   # money out → negative
        elif txn_type in REDEMPTION_TYPES:
            signed = abs(amt)    # money in  → positive
        else:
            continue  # dividends etc. — excluded from XIRR

        fund_map[fund_name].append((txn_date, signed))

    return dict(fund_map)


def get_portfolio_cashflows(
    db: Session,
    user_id: str,
) -> List[Tuple[date, float]]:
    """
    Return all cashflows merged across all funds, sorted by date.
    Used for portfolio-level XIRR.
    """
    all_cf: List[Tuple[date, float]] = []
    for cfs in get_fund_cashflows(db, user_id).values():
        all_cf.extend(cfs)
    all_cf.sort(key=lambda x: x[0])
    return all_cf


# ── Current value builders ─────────────────────────────────────────────────────

def get_fund_current_values(
    db: Session,
    user_id: str,
) -> Dict[str, float]:
    """
    Return current market value per fund:
        value = net_current_units × latest_nav (from nav_cache)

    Fallback for unmatched funds (scheme_code NULL / no NAV cache):
        value = most recent (current_units × nav_at_transaction) from portfolio rows.
    This ensures XIRR/CAGR/AbsRet are computable even for unmatched funds.
    """
    # ── Matched funds: use nav_cache ──────────────────────────────────────────
    matched_rows = (
        db.query(
            Portfolio.fund_name,
            Portfolio.scheme_code,
            func.max(Portfolio.current_units).label("net_units"),
        )
        .filter(
            Portfolio.user_id == user_id,
            Portfolio.scheme_code.isnot(None),
            Portfolio.current_units.isnot(None),
        )
        .group_by(Portfolio.fund_name, Portfolio.scheme_code)
        .all()
    )

    result: Dict[str, float] = {}
    for fund_name, scheme_code, net_units in matched_rows:
        if not net_units or float(net_units) <= 0:
            result[fund_name] = 0.0
            continue
        cached = db.query(NavCache).filter(NavCache.scheme_code == scheme_code).first()
        if cached and cached.current_nav:
            result[fund_name] = float(net_units) * float(cached.current_nav)
        else:
            # NAV cache miss — fall through to fallback below
            result[fund_name] = 0.0

    # ── Unmatched funds: fallback using latest nav_at_transaction ─────────────
    # Find all funds not already in result (scheme_code is NULL or NAV was 0)
    all_fund_names_rows = (
        db.query(Portfolio.fund_name)
        .filter(Portfolio.user_id == user_id)
        .distinct()
        .all()
    )
    all_fund_names = {r[0] for r in all_fund_names_rows}
    missing_funds = all_fund_names - set(result.keys())

    # Also re-check matched funds whose nav_cache returned 0
    zero_funds = {fn for fn, val in result.items() if val == 0.0}
    funds_to_estimate = missing_funds | zero_funds

    for fund_name in funds_to_estimate:
        # Get most recent row with non-null current_units AND nav_at_transaction
        latest = (
            db.query(Portfolio)
            .filter(
                Portfolio.user_id == user_id,
                Portfolio.fund_name == fund_name,
                Portfolio.current_units.isnot(None),
                Portfolio.nav_at_transaction.isnot(None),
            )
            .order_by(Portfolio.transaction_date.desc())
            .first()
        )
        if latest and latest.current_units and latest.nav_at_transaction:
            net_units = float(latest.current_units)
            nav = float(latest.nav_at_transaction)
            if net_units > 0 and nav > 0:
                result[fund_name] = round(net_units * nav, 2)
            else:
                result[fund_name] = 0.0
        else:
            result[fund_name] = 0.0

    return result


def get_total_portfolio_value(db: Session, user_id: str) -> float:
    """Sum of current values across all funds."""
    return sum(get_fund_current_values(db, user_id).values())


# ── Invested amount helpers ────────────────────────────────────────────────────

def get_fund_invested_amounts(
    db: Session,
    user_id: str,
) -> Dict[str, float]:
    """
    Gross amount invested per fund (purchases only, absolute value).
    Does NOT subtract redemptions — shows total capital deployed.
    """
    rows = (
        db.query(
            Portfolio.fund_name,
            func.coalesce(func.sum(Portfolio.amount_inr), 0).label("invested"),
        )
        .filter(
            Portfolio.user_id == user_id,
            Portfolio.transaction_type.in_(PURCHASE_TYPES),
            Portfolio.amount_inr.isnot(None),
        )
        .group_by(Portfolio.fund_name)
        .all()
    )
    # Use Python-side abs() because old DB data may have negative amounts
    # from the previous parser bug where brackets produced negative values.
    result = {}
    for fund_name, invested in rows:
        result[fund_name] = abs(float(invested))
    return result


def get_total_invested(db: Session, user_id: str) -> float:
    """Total gross amount invested across all funds."""
    return sum(get_fund_invested_amounts(db, user_id).values())


# ── Portfolio growth time series ───────────────────────────────────────────────

def get_portfolio_growth_series(
    db: Session,
    user_id: str,
) -> List[Dict]:
    """
    Build a cumulative time series for the Portfolio Growth chart.

    Each point: { date, invested_amount (cumulative), current_value (snapshot) }

    Only fetch PURCHASE rows for the invested-amount series.
    Redemptions are NOT subtracted — the "invested amount" line shows cumulative
    capital deployed over time (how much money went in), not net position.
    This is standard portfolio growth chart convention.
    """
    purchase_rows = (
        db.query(
            Portfolio.transaction_date,
            Portfolio.amount_inr,
        )
        .filter(
            Portfolio.user_id == user_id,
            Portfolio.amount_inr.isnot(None),
            Portfolio.transaction_date.isnot(None),
            Portfolio.transaction_type.in_(list(PURCHASE_TYPES)),
        )
        .order_by(Portfolio.transaction_date.asc())
        .all()
    )

    if not purchase_rows:
        return []

    total_current = get_total_portfolio_value(db, user_id)
    total_invested = get_total_invested(db, user_id)   # gross purchases only

    # Build cumulative gross-invested series (monthly granularity)
    cumulative = 0.0
    points = []
    seen_months = set()

    for txn_date, amount in purchase_rows:
        amt = abs(float(amount))   # always positive
        cumulative += amt

        month_key = (txn_date.year, txn_date.month)
        if month_key in seen_months:
            # Update the existing month point with the latest cumulative
            if points:
                points[-1]["invested_amount"] = round(cumulative, 2)
        else:
            seen_months.add(month_key)
            points.append({
                "date": txn_date.isoformat(),
                "invested_amount": round(cumulative, 2),
            })

    if not points:
        return []

    # Scale current_value proportionally at each historical point.
    # ratio = current_total / gross_invested  (e.g. 0.9 = portfolio is at 90% of cost)
    ratio = (total_current / total_invested) if total_invested > 0 else 1.0
    for p in points:
        p["current_value"] = round(p["invested_amount"] * ratio, 2)

    # Ensure the last point uses the exact current value (not a ratio estimate)
    today = date.today().isoformat()
    if points and points[-1]["date"] != today:
        points.append({
            "date": today,
            "invested_amount": round(cumulative, 2),
            "current_value": round(total_current, 2),
        })
    elif points:
        points[-1]["current_value"] = round(total_current, 2)

    return points


# ── Per-fund summary ───────────────────────────────────────────────────────────

def get_fund_summary_rows(db: Session, user_id: str) -> List[Dict]:
    """
    Return a list of per-fund summary dicts containing:
      fund_name, scheme_code, invested, current_value, cashflows, first_date, last_date
    """
    cashflows = get_fund_cashflows(db, user_id)
    invested = get_fund_invested_amounts(db, user_id)
    current_values = get_fund_current_values(db, user_id)

    # Get scheme codes and date ranges in one query
    meta_rows = (
        db.query(
            Portfolio.fund_name,
            Portfolio.scheme_code,
            func.min(Portfolio.transaction_date).label("first_date"),
            func.max(Portfolio.transaction_date).label("last_date"),
        )
        .filter(Portfolio.user_id == user_id)
        .group_by(Portfolio.fund_name, Portfolio.scheme_code)
        .all()
    )

    result = []
    for fund_name, scheme_code, first_date, last_date in meta_rows:
        result.append({
            "fund_name": fund_name,
            "scheme_code": scheme_code,
            "invested": invested.get(fund_name, 0.0),
            "current_value": current_values.get(fund_name, 0.0),
            "cashflows": cashflows.get(fund_name, []),
            "first_date": first_date,
            "last_date": last_date,
        })

    return result
