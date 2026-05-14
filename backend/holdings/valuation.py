"""
Holdings Valuation — attaches live NAV and daily P&L to HoldingRecord objects.

Valuation chain:
  1. Try nav_cache (refreshed every 4 h by portfolio.py)
  2. Fall back to nav_at_transaction (last known NAV from PDF)
  3. If neither available: current_value = 0, gains = 0

Daily gain uses nav_cache.previous_nav (yesterday's NAV).
Since nav_cache only stores current NAV, we fetch the previous trading day's
NAV from historical_nav_cache for the daily change.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import NavCache, HistoricalNavCache, Portfolio
from holdings.reconstructor import HoldingRecord

logger = logging.getLogger(__name__)


def _get_previous_nav(db: Session, scheme_code: str, today: date) -> Optional[float]:
    """
    Return the most recent NAV before today from historical_nav_cache.
    Looks back up to 7 days to handle weekends/holidays.
    """
    for delta in range(1, 8):
        prev_date = today - timedelta(days=delta)
        row = (
            db.query(HistoricalNavCache)
            .filter(
                HistoricalNavCache.scheme_code == scheme_code,
                HistoricalNavCache.nav_date == prev_date,
            )
            .first()
        )
        if row:
            return float(row.nav_value)
    return None


def attach_valuations(
    db: Session,
    holdings: List[HoldingRecord],
) -> List[HoldingRecord]:
    """
    Attach current_nav, current_value, unrealized_gain, daily_gain to each holding.
    Modifies records in-place and returns the same list.
    """
    today = date.today()

    # Bulk-load nav_cache for all scheme codes in one query
    scheme_codes = [h.scheme_code for h in holdings if h.scheme_code]
    nav_map: Dict[str, float] = {}
    if scheme_codes:
        cache_rows = (
            db.query(NavCache)
            .filter(NavCache.scheme_code.in_(scheme_codes))
            .all()
        )
        for row in cache_rows:
            if row.current_nav:
                nav_map[row.scheme_code] = float(row.current_nav)

    for rec in holdings:
        if rec.current_units <= 0.001:
            # Fully redeemed — keep zero valuation
            rec.current_value   = 0.0
            rec.unrealized_gain = rec.realized_gain  # all gain is realized
            continue

        # Resolve current NAV
        current_nav: Optional[float] = None

        if rec.scheme_code and rec.scheme_code in nav_map:
            current_nav = nav_map[rec.scheme_code]
        else:
            # Fallback: fetch most recent nav_at_transaction for this fund
            latest_row = (
                db.query(Portfolio.nav_at_transaction)
                .filter(
                    Portfolio.user_id   == None,   # placeholder — see note below
                    Portfolio.fund_name == rec.fund_name,
                    Portfolio.nav_at_transaction.isnot(None),
                )
                .order_by(Portfolio.transaction_date.desc())
                .first()
            )
            # Note: user_id filter is not available here — we use rec data only
            # The fallback is best-effort; unmatched funds will show stale NAV
            if latest_row and latest_row[0]:
                current_nav = float(latest_row[0])

        if current_nav is None or current_nav <= 0:
            rec.current_value   = 0.0
            rec.unrealized_gain = 0.0
            rec.unrealized_pct  = 0.0
            continue

        rec.current_nav   = current_nav
        rec.current_value = round(rec.current_units * current_nav, 2)

        # Unrealized gain = current value - cost of currently held units
        cost_of_held = rec.current_units * (rec.avg_buy_nav or current_nav)
        rec.unrealized_gain = round(rec.current_value - cost_of_held, 2)
        if cost_of_held > 0:
            rec.unrealized_pct = round(rec.unrealized_gain / cost_of_held * 100, 2)

        # Daily gain: needs previous day NAV from historical_nav_cache
        if rec.scheme_code:
            prev_nav = _get_previous_nav(db, rec.scheme_code, today)
            if prev_nav and prev_nav > 0:
                nav_change    = current_nav - prev_nav
                rec.daily_gain     = round(rec.current_units * nav_change, 2)
                rec.daily_gain_pct = round(nav_change / prev_nav * 100, 4)

    return holdings


def compute_portfolio_summary(holdings: List[HoldingRecord]) -> dict:
    """
    Aggregate holdings into a single portfolio-level summary dict.
    """
    total_invested  = sum(h.invested_amount for h in holdings)
    total_value     = sum(h.current_value   for h in holdings)
    total_daily_gain = sum(h.daily_gain     for h in holdings)
    total_realized   = sum(h.realized_gain  for h in holdings)
    unrealized       = sum(h.unrealized_gain for h in holdings)
    total_pnl        = unrealized + total_realized

    abs_return_pct = 0.0
    if total_invested > 0:
        abs_return_pct = round((total_value - total_invested) / total_invested * 100, 2)

    daily_gain_pct = 0.0
    prev_value = total_value - total_daily_gain
    if prev_value > 0:
        daily_gain_pct = round(total_daily_gain / prev_value * 100, 4)

    return {
        "total_invested":    round(total_invested,   2),
        "total_value":       round(total_value,      2),
        "total_pnl":         round(total_pnl,        2),
        "unrealized_gain":   round(unrealized,       2),
        "realized_gain":     round(total_realized,   2),
        "daily_gain":        round(total_daily_gain, 2),
        "daily_gain_pct":    daily_gain_pct,
        "abs_return_pct":    abs_return_pct,
        "num_funds":         sum(1 for h in holdings if not h.is_fully_redeemed),
        "num_redeemed":      sum(1 for h in holdings if h.is_fully_redeemed),
    }
