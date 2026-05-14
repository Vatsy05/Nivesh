"""
XIRR, CAGR, and Absolute Return computation engine.

Uses pyxirr for XIRR (handles irregular cashflow dates correctly).
All functions return None on invalid input — callers must handle None gracefully.

XIRR sign convention (standard finance):
  investments  → negative cashflows
  terminal value / redemptions → positive cashflows
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── XIRR ─────────────────────────────────────────────────────────────────────

def compute_xirr(
    cashflows: List[Tuple[date, float]],
    terminal_value: float,
    as_of: Optional[date] = None,
) -> Optional[float]:
    """
    Compute XIRR given a list of (date, signed_amount) cashflows and a terminal value.

    Args:
        cashflows:      [(date, amount)] — investments negative, redemptions positive
        terminal_value: current market value (added as a positive cashflow at as_of)
        as_of:          date of the terminal value; defaults to today

    Returns:
        XIRR as a decimal (e.g. 0.1423 = 14.23%), or None if not computable.
    """
    try:
        from pyxirr import xirr as _xirr, InvalidPaymentsError
    except ImportError:
        logger.error("pyxirr not installed — cannot compute XIRR")
        return None

    if not cashflows:
        return None

    if as_of is None:
        as_of = date.today()

    # Filter out zero-amount entries
    clean = [(d, a) for d, a in cashflows if a != 0.0]
    if not clean:
        return None

    # Need at least 1 negative (investment) and 1 positive (value/redemption)
    negatives = [a for _, a in clean if a < 0]
    if not negatives:
        return None  # redemption-only — no investment to compute XIRR on

    total_invested = abs(sum(negatives))
    if total_invested == 0:
        return None

    if terminal_value <= 0:
        # Zero or negative current value — can still compute if redemptions > 0
        positives = [a for _, a in clean if a > 0]
        if not positives:
            return None

    # Build final cashflow list with terminal value
    dates = [d for d, _ in clean]
    amounts = [a for _, a in clean]

    # Append terminal value as positive cashflow today
    if terminal_value > 0:
        dates.append(as_of)
        amounts.append(terminal_value)

    # Minimum 2 cashflows required
    if len(dates) < 2:
        return None

    # Must have at least one sign change
    has_neg = any(a < 0 for a in amounts)
    has_pos = any(a > 0 for a in amounts)
    if not (has_neg and has_pos):
        return None

    try:
        result = _xirr(dates, amounts)
        if result is None:
            return None
        # Sanity check: XIRR outside [-99%, +1000%] is almost certainly wrong
        if not (-0.99 < result < 10.0):
            logger.warning(f"XIRR out of reasonable range: {result:.4f} — returning None")
            return None
        return round(float(result), 6)
    except InvalidPaymentsError:
        logger.warning("pyxirr: InvalidPaymentsError — cashflows may have wrong signs")
        return None
    except Exception as e:
        logger.warning(f"pyxirr failed: {e}")
        return None


# ── CAGR ──────────────────────────────────────────────────────────────────────

def compute_cagr(
    first_investment_date: date,
    invested_amount: float,
    current_value: float,
    as_of: Optional[date] = None,
) -> Optional[float]:
    """
    Compute CAGR (Compound Annual Growth Rate).

    Formula: (current_value / invested_amount) ^ (1 / years) - 1

    Note: This is a simplified CAGR using total invested vs current value.
    For lumpsum-style comparison, it is accurate.
    For SIP portfolios, prefer XIRR (which accounts for timing).

    Returns decimal (e.g. 0.1423 = 14.23%), or None if not computable.
    """
    if as_of is None:
        as_of = date.today()

    if invested_amount is None or invested_amount <= 0:
        return None
    if current_value is None or current_value < 0:
        return None
    if first_investment_date is None:
        return None

    days = (as_of - first_investment_date).days
    if days <= 0:
        return None

    years = days / 365.25

    if years < (1 / 365.25):  # less than 1 day
        return None

    try:
        ratio = current_value / invested_amount
        if ratio <= 0:
            return None
        cagr = ratio ** (1.0 / years) - 1.0
        # Sanity clamp
        if not (-0.99 < cagr < 10.0):
            return None
        return round(cagr, 6)
    except (ZeroDivisionError, ValueError, OverflowError) as e:
        logger.warning(f"CAGR computation failed: {e}")
        return None


# ── Absolute Return ────────────────────────────────────────────────────────────

def compute_absolute_return(
    invested_amount: float,
    current_value: float,
) -> Optional[float]:
    """
    Compute absolute return percentage.

    Formula: ((current_value - invested_amount) / invested_amount) × 100

    Returns percentage float (e.g. 34.21 = 34.21%), or None if not computable.
    """
    if invested_amount is None or invested_amount <= 0:
        return None
    if current_value is None or current_value < 0:
        return None

    try:
        return round(((current_value - invested_amount) / invested_amount) * 100.0, 4)
    except ZeroDivisionError:
        return None


# ── Convenience wrapper ───────────────────────────────────────────────────────

def compute_all_metrics(
    cashflows: List[Tuple[date, float]],
    invested_amount: float,
    current_value: float,
    first_date: Optional[date] = None,
) -> dict:
    """
    Compute XIRR, CAGR, and absolute return in one call.

    Returns dict with keys: xirr, xirr_pct, cagr, cagr_pct, absolute_return_pct
    All values are None if not computable.
    """
    today = date.today()

    xirr_val = compute_xirr(cashflows, current_value, as_of=today)
    xirr_pct = round(xirr_val * 100, 4) if xirr_val is not None else None

    # Use first cashflow date if not explicitly provided
    if first_date is None and cashflows:
        first_date = min(d for d, _ in cashflows)

    cagr_val = compute_cagr(first_date, invested_amount, current_value, as_of=today)
    cagr_pct = round(cagr_val * 100, 4) if cagr_val is not None else None

    abs_ret = compute_absolute_return(invested_amount, current_value)

    return {
        "xirr": xirr_val,
        "xirr_pct": xirr_pct,
        "cagr": cagr_val,
        "cagr_pct": cagr_pct,
        "absolute_return_pct": abs_ret,
    }
