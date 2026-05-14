"""
Snapshot Engine — computes daily portfolio valuation history and stores it
in portfolio_snapshots for fast chart rendering.

Algorithm (for each day from first_transaction to today):
  1. Reconstruct holdings as of that date (units held via transactions ≤ date)
  2. For each fund, look up NAV for that date in historical_nav_cache
     (forward-fill missing dates for weekends/holidays)
  3. Compute portfolio_value = sum(units × nav)
  4. Compute invested_amount = sum of purchase amounts up to that date
  5. Write to portfolio_snapshots (upsert)

Optimizations:
  - All historical NAVs are loaded once into pandas DataFrames (one per scheme)
  - Transaction history is built once as a sorted list
  - Pandas vectorized forward-fill for NAV gaps
  - Snapshots are reused if already fresh (skips computation if last snapshot is today)
  - Monthly granularity for data older than 90 days to reduce row count
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Portfolio, HistoricalNavCache

logger = logging.getLogger(__name__)

PURCHASE_TYPES   = {"SIP", "lumpsum", "switch_in"}
REDEMPTION_TYPES = {"redemption", "switch_out"}
DAILY_CUTOFF_DAYS = 90    # daily snapshots for recent 90 days, monthly before that


def _load_all_nav_histories(
    db: Session,
    scheme_codes: List[str],
) -> Dict[str, pd.Series]:
    """
    Load historical NAV for all scheme codes into pandas Series (date-indexed).
    Returns dict: scheme_code → pd.Series with DatetimeIndex, forward-filled.
    """
    if not scheme_codes:
        return {}

    rows = (
        db.query(
            HistoricalNavCache.scheme_code,
            HistoricalNavCache.nav_date,
            HistoricalNavCache.nav_value,
        )
        .filter(HistoricalNavCache.scheme_code.in_(scheme_codes))
        .all()
    )

    if not rows:
        return {}

    df = pd.DataFrame(rows, columns=["scheme_code", "date", "nav"])
    df["date"] = pd.to_datetime(df["date"])
    df["nav"]  = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna(subset=["nav"])

    result: Dict[str, pd.Series] = {}
    for code, group in df.groupby("scheme_code"):
        s = group.set_index("date")["nav"].sort_index()
        result[str(code)] = s

    return result


def _get_nav_on_date(
    nav_series: pd.Series,
    target_date: date,
) -> Optional[float]:
    """
    Return NAV for target_date. Uses .asof() for forward-fill on missing dates.
    """
    ts = pd.Timestamp(target_date)
    if nav_series.empty or ts < nav_series.index[0]:
        return None
    try:
        val = nav_series.asof(ts)
        return float(val) if not pd.isna(val) else None
    except Exception:
        return None


def _get_snapshot_dates(first_date: date, today: date) -> List[date]:
    """
    Generate the list of dates to snapshot:
    - Monthly for dates older than DAILY_CUTOFF_DAYS ago
    - Daily for the recent DAILY_CUTOFF_DAYS
    """
    cutoff = today - timedelta(days=DAILY_CUTOFF_DAYS)
    dates: List[date] = []
    current = first_date

    while current <= today:
        if current < cutoff:
            # Monthly: jump to first of next month
            dates.append(current)
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)
        else:
            dates.append(current)
            current += timedelta(days=1)

    return dates


def compute_and_store_snapshots(
    db: Session,
    user_id: str,
    force: bool = False,
) -> List[dict]:
    """
    Compute daily portfolio snapshots and store in portfolio_snapshots.
    Returns the final series as a list of dicts for API response.

    If snapshots already exist and are fresh (last snapshot = today), returns
    cached data unless force=True.
    """
    today = date.today()

    # Check if snapshots are already fresh
    if not force:
        try:
            latest_snapshot = db.execute(
                text(
                    "SELECT snapshot_date FROM portfolio_snapshots "
                    "WHERE user_id = :uid ORDER BY snapshot_date DESC LIMIT 1"
                ),
                {"uid": user_id},
            ).fetchone()

            # Detect stale snapshots: if a transaction is newer than the latest
            # snapshot, the user re-uploaded a PDF and we must rebuild.
            latest_txn_row = db.execute(
                text(
                    "SELECT MAX(transaction_date) FROM portfolios WHERE user_id = :uid"
                ),
                {"uid": user_id},
            ).fetchone()

            latest_txn_date = latest_txn_row[0] if latest_txn_row else None

            if latest_snapshot and latest_snapshot[0] == today:
                # Also check that no new transactions appeared after last snapshot
                if latest_txn_date and latest_txn_date <= latest_snapshot[0]:
                    logger.info(f"Snapshots fresh for user {user_id[:8]}, returning cached")
                    return _load_snapshots_from_db(db, user_id)
                else:
                    logger.info(f"New transactions detected after last snapshot — rebuilding")
            elif latest_snapshot and not latest_txn_date:
                logger.info(f"Snapshots exist but no transactions — returning cached")
                return _load_snapshots_from_db(db, user_id)
        except Exception as e:
            # portfolio_snapshots table may not exist yet (pre-migration)
            logger.warning(f"Snapshot cache check failed (table may not exist): {e}")
            # Fall through to compute (will fail gracefully if table missing)
            return []

    # Load all transactions for this user (sorted)
    txn_rows = (
        db.query(
            Portfolio.fund_name,
            Portfolio.scheme_code,
            Portfolio.transaction_type,
            Portfolio.transaction_date,
            Portfolio.amount_inr,
            Portfolio.units,
        )
        .filter(
            Portfolio.user_id == user_id,
            Portfolio.transaction_date.isnot(None),
        )
        .order_by(Portfolio.transaction_date.asc())
        .all()
    )

    if not txn_rows:
        return []

    first_date = txn_rows[0].transaction_date
    if isinstance(first_date, str):
        from datetime import datetime as _dt
        first_date = _dt.fromisoformat(first_date).date()

    # Get all scheme codes with historical NAV data
    scheme_codes = list({
        row.scheme_code for row in txn_rows
        if row.scheme_code
    })
    nav_histories = _load_all_nav_histories(db, scheme_codes)

    if not nav_histories:
        logger.warning(f"No historical NAV data for user {user_id[:8]} — returning empty snapshots")
        return []

    # Build snapshot dates
    snapshot_dates = _get_snapshot_dates(first_date, today)

    # Compute snapshots using cumulative unit tracking
    fund_units: Dict[str, float] = {}    # scheme_code → running units
    fund_invested: Dict[str, float] = {} # scheme_code → running invested
    fund_names_map: Dict[str, str] = {}  # scheme_code → fund_name
    txn_idx = 0
    n_txns = len(txn_rows)
    snapshots: List[dict] = []
    prev_value: Optional[float] = None

    for snap_date in snapshot_dates:
        # Consume all transactions up to and including snap_date
        while txn_idx < n_txns:
            row = txn_rows[txn_idx]
            txn_date = row.transaction_date
            if isinstance(txn_date, str):
                from datetime import datetime as _dt
                txn_date = _dt.fromisoformat(txn_date).date()

            if txn_date > snap_date:
                break

            sc = row.scheme_code
            if not sc:
                txn_idx += 1
                continue

            fund_names_map[sc] = row.fund_name
            u   = abs(float(row.units))      if row.units      else 0.0
            amt = abs(float(row.amount_inr)) if row.amount_inr else 0.0

            if row.transaction_type in PURCHASE_TYPES:
                fund_units[sc]    = fund_units.get(sc, 0.0)    + u
                fund_invested[sc] = fund_invested.get(sc, 0.0) + amt

            elif row.transaction_type in REDEMPTION_TYPES:
                fund_units[sc] = max(0.0, fund_units.get(sc, 0.0) - u)

            txn_idx += 1

        # Compute portfolio value on this date
        portfolio_value = 0.0
        invested_amount = sum(fund_invested.values())

        for sc, units in fund_units.items():
            if units <= 0.001:
                continue
            nav_series = nav_histories.get(sc)
            if nav_series is None:
                continue
            nav = _get_nav_on_date(nav_series, snap_date)
            if nav and nav > 0:
                portfolio_value += units * nav

        # Daily P&L
        daily_pnl = round(portfolio_value - prev_value, 2) if prev_value is not None else 0.0
        total_pnl = round(portfolio_value - invested_amount, 2) if invested_amount > 0 else 0.0
        prev_value = portfolio_value

        snapshots.append({
            "date":             snap_date.isoformat(),
            "invested_amount":  round(invested_amount, 2),
            "portfolio_value":  round(portfolio_value, 2),
            "daily_pnl":        daily_pnl,
            "total_pnl":        total_pnl,
        })

    if not snapshots:
        return []

    # Upsert into portfolio_snapshots table
    _upsert_snapshots(db, user_id, snapshots)

    # Filter out zero-value points at the start (no NAV data yet)
    non_zero = [s for s in snapshots if s["portfolio_value"] > 0 or s["invested_amount"] > 0]
    return non_zero


def _upsert_snapshots(db: Session, user_id: str, snapshots: List[dict]) -> None:
    """Bulk upsert snapshots into portfolio_snapshots table."""
    try:
        for s in snapshots:
            db.execute(
                text("""
                    INSERT INTO portfolio_snapshots
                        (user_id, snapshot_date, invested_amount, portfolio_value, daily_pnl, total_pnl)
                    VALUES
                        (:uid, :date, :invested, :value, :daily_pnl, :total_pnl)
                    ON CONFLICT (user_id, snapshot_date)
                    DO UPDATE SET
                        invested_amount = EXCLUDED.invested_amount,
                        portfolio_value = EXCLUDED.portfolio_value,
                        daily_pnl       = EXCLUDED.daily_pnl,
                        total_pnl       = EXCLUDED.total_pnl
                """),
                {
                    "uid":       user_id,
                    "date":      s["date"],
                    "invested":  s["invested_amount"],
                    "value":     s["portfolio_value"],
                    "daily_pnl": s["daily_pnl"],
                    "total_pnl": s["total_pnl"],
                },
            )
        db.commit()
        logger.info(f"Upserted {len(snapshots)} snapshots for user")
    except Exception as e:
        db.rollback()
        logger.error(f"Snapshot upsert failed: {e}")


def _load_snapshots_from_db(db: Session, user_id: str) -> List[dict]:
    """Load cached snapshots from DB, ordered ascending by date."""
    try:
        rows = db.execute(
            text("""
                SELECT snapshot_date, invested_amount, portfolio_value, daily_pnl, total_pnl
                FROM portfolio_snapshots
                WHERE user_id = :uid
                ORDER BY snapshot_date ASC
            """),
            {"uid": user_id},
        ).fetchall()

        return [
            {
                "date":            str(r[0]),
                "invested_amount": float(r[1]) if r[1] else 0.0,
                "portfolio_value": float(r[2]) if r[2] else 0.0,
                "daily_pnl":       float(r[3]) if r[3] else 0.0,
                "total_pnl":       float(r[4]) if r[4] else 0.0,
            }
            for r in rows
            if (r[2] or 0) > 0 or (r[1] or 0) > 0
        ]
    except Exception as e:
        logger.warning(f"Could not load snapshots from DB: {e}")
        return []


def clear_snapshots(db: Session, user_id: str) -> None:
    """Delete all snapshots for a user (called on PDF re-upload)."""
    try:
        db.execute(
            text("DELETE FROM portfolio_snapshots WHERE user_id = :uid"),
            {"uid": user_id},
        )
        db.commit()
        logger.info(f"Cleared snapshots for user {user_id[:8]}")
    except Exception as e:
        db.rollback()
        logger.error(f"Snapshot clear failed: {e}")
