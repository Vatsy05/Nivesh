"""
Rolling returns engine — fetches and caches historical NAV from mfapi.in,
then computes 1Y/3Y/5Y rolling returns and point-to-point returns using pandas.

Caching strategy:
  1. Check historical_nav_cache table (SQLAlchemy ORM via HistoricalNavCache model)
  2. If missing or stale (>24 h), fetch from mfapi.in and upsert
  3. All rolling computations are vectorized pandas operations
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import httpx
import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import HistoricalNavCache

logger = logging.getLogger(__name__)

MFAPI_BASE = "https://api.mfapi.in/mf"
CACHE_STALENESS_HOURS = 24
ROLLING_WINDOWS = {
    "1Y": 365,
    "3Y": 3 * 365,
    "5Y": 5 * 365,
}


# ── NAV Fetching & Caching ─────────────────────────────────────────────────────

async def fetch_historical_nav(scheme_code: str, db: Session) -> pd.DataFrame:
    """
    Return historical NAV as a DataFrame with columns [date, nav].
    Fetches from DB cache first; falls back to mfapi.in if stale or missing.

    Returns empty DataFrame on failure.
    """
    # Check cache freshness
    cached_rows = (
        db.query(HistoricalNavCache)
        .filter(HistoricalNavCache.scheme_code == scheme_code)
        .order_by(HistoricalNavCache.nav_date.desc())
        .limit(1)
        .all()
    )

    needs_refresh = True
    if cached_rows:
        latest = cached_rows[0]
        age = datetime.utcnow() - (latest.last_fetched or datetime.min)
        if age < timedelta(hours=CACHE_STALENESS_HOURS):
            needs_refresh = False
            logger.debug(f"NAV cache fresh for {scheme_code} (age: {age})")

    if needs_refresh:
        logger.info(f"Fetching historical NAV from mfapi.in for scheme {scheme_code}")
        raw = await _fetch_from_mfapi(scheme_code)
        if raw:
            _upsert_nav_cache(db, scheme_code, raw)
            logger.info(f"Cached {len(raw)} NAV rows for {scheme_code}")

    # Load from DB
    return _load_nav_from_db(db, scheme_code)


async def _fetch_from_mfapi(scheme_code: str) -> List[dict]:
    """Call mfapi.in and return list of {date: str, nav: str} dicts."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{MFAPI_BASE}/{scheme_code}")
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
    except httpx.HTTPError as e:
        logger.error(f"mfapi.in historical NAV fetch failed for {scheme_code}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching NAV history for {scheme_code}: {e}")
        return []


def _upsert_nav_cache(db: Session, scheme_code: str, raw: List[dict]) -> None:
    """Bulk upsert historical NAV rows into historical_nav_cache.

    The previous row-by-row SELECT+INSERT/UPDATE approach issued ~3000 DB
    round-trips per scheme and blocked the event loop for tens of seconds,
    causing the dashboard /holdings/summary fetch to time out. We now use a
    single PostgreSQL INSERT ... ON CONFLICT DO UPDATE which writes the
    whole batch in one statement.
    """
    if not raw:
        return

    now = datetime.utcnow()
    rows: List[dict] = []
    for row in raw:
        try:
            nav_date = datetime.strptime(row["date"], "%d-%m-%Y").date()
            nav_value = float(row["nav"])
        except (KeyError, ValueError):
            continue
        rows.append({
            "scheme_code": scheme_code,
            "nav_date": nav_date,
            "nav_value": nav_value,
            "last_fetched": now,
        })

    if not rows:
        return

    # PostgreSQL bulk UPSERT — one statement, no per-row roundtrip.
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    stmt = pg_insert(HistoricalNavCache).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["scheme_code", "nav_date"],
        set_={
            "nav_value": stmt.excluded.nav_value,
            "last_fetched": stmt.excluded.last_fetched,
        },
    )
    db.execute(stmt)
    db.commit()


def _load_nav_from_db(db: Session, scheme_code: str) -> pd.DataFrame:
    """Load historical NAV rows into a pandas DataFrame."""
    rows = (
        db.query(HistoricalNavCache.nav_date, HistoricalNavCache.nav_value)
        .filter(HistoricalNavCache.scheme_code == scheme_code)
        .order_by(HistoricalNavCache.nav_date.asc())
        .all()
    )
    if not rows:
        return pd.DataFrame(columns=["date", "nav"])

    df = pd.DataFrame(rows, columns=["date", "nav"])
    df["date"] = pd.to_datetime(df["date"])
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna(subset=["nav"]).sort_values("date").reset_index(drop=True)
    return df


# ── Rolling Returns ────────────────────────────────────────────────────────────

def compute_rolling_returns(
    nav_df: pd.DataFrame,
    window_days: int,
) -> pd.DataFrame:
    """
    Compute rolling returns for a given window (in days).

    For each date t, rolling return = (NAV[t] / NAV[t - window_days]) - 1

    Returns DataFrame with columns [date, return_pct].
    return_pct is expressed as a percentage (e.g. 14.23 = 14.23%).
    """
    if nav_df.empty or len(nav_df) < 2:
        return pd.DataFrame(columns=["date", "return_pct"])

    df = nav_df.set_index("date").copy()
    df.index = pd.to_datetime(df.index)

    # Create date-indexed series with forward-fill for missing dates
    full_idx = pd.date_range(df.index.min(), df.index.max(), freq="D")
    nav_series = df["nav"].reindex(full_idx).ffill()

    # Shift by window days
    shifted = nav_series.shift(window_days)
    rolling_return = ((nav_series / shifted) - 1) * 100

    result = rolling_return.dropna().reset_index()
    result.columns = ["date", "return_pct"]
    result["date"] = result["date"].dt.strftime("%Y-%m-%d")
    result["return_pct"] = result["return_pct"].round(4)

    # Downsample to monthly to reduce payload size
    result["_date"] = pd.to_datetime(result["date"])
    result = result.groupby(result["_date"].dt.to_period("M")).last().reset_index(drop=True)
    result = result.drop(columns=["_date"])

    return result


def compute_rolling_summary(nav_df: pd.DataFrame) -> Dict[str, Optional[Dict]]:
    """
    Compute min/max/median rolling return for each standard window (1Y, 3Y, 5Y).

    Returns:
        {
            "1Y": {"min": float, "max": float, "median": float, "current": float},
            "3Y": {...},
            "5Y": {...},
        }
    """
    summary = {}
    for label, days in ROLLING_WINDOWS.items():
        rolls = compute_rolling_returns(nav_df, days)
        if rolls.empty:
            summary[label] = None
            continue

        series = rolls["return_pct"]
        summary[label] = {
            "min": round(float(series.min()), 4),
            "max": round(float(series.max()), 4),
            "median": round(float(series.median()), 4),
            "current": round(float(series.iloc[-1]), 4),
        }
    return summary


def compute_rolling_series_all_windows(
    nav_df: pd.DataFrame,
) -> Dict[str, List[Dict]]:
    """
    Return rolling return time series for all windows.
    Each series is a list of {date, return_pct} dicts.
    """
    result = {}
    for label, days in ROLLING_WINDOWS.items():
        rolls = compute_rolling_returns(nav_df, days)
        result[label] = rolls.to_dict(orient="records") if not rolls.empty else []
    return result


# ── Point-to-Point Return ──────────────────────────────────────────────────────

def compute_p2p_return(
    nav_df: pd.DataFrame,
    start_date: date,
    end_date: date,
) -> Optional[float]:
    """
    Compute point-to-point return between two dates.
    Uses nearest available NAV if exact date is missing (forward-fill).

    Returns: percentage float (e.g. 34.21 = 34.21%), or None on failure.
    """
    if nav_df.empty:
        return None

    df = nav_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").set_index("date")

    full_idx = pd.date_range(df.index.min(), max(df.index.max(), pd.Timestamp(end_date)), freq="D")
    nav_series = df["nav"].reindex(full_idx).ffill()

    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)

    if start_ts < nav_series.index[0] or end_ts < nav_series.index[0]:
        return None

    try:
        nav_start = nav_series.asof(start_ts)
        nav_end = nav_series.asof(end_ts)
        if pd.isna(nav_start) or pd.isna(nav_end) or nav_start == 0:
            return None
        return round(((nav_end / nav_start) - 1) * 100, 4)
    except Exception as e:
        logger.warning(f"P2P return computation failed: {e}")
        return None
