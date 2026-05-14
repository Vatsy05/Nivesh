"""
Holdings Reconstructor — derives current holdings from raw transaction history.

For each (user_id, fund_name, scheme_code) group:

  purchase_units   = SUM(units) WHERE type IN {SIP, lumpsum, switch_in}
  redemption_units = SUM(units) WHERE type IN {redemption, switch_out}
  current_units    = purchase_units - redemption_units   (≥ 0)

  invested_amount  = SUM(abs(amount_inr)) WHERE type IN purchases
  avg_buy_nav      = invested_amount / purchase_units
  realized_gain    = SUM(abs(amount_inr)) WHERE type IN redemptions
                     - (redeemed_units × avg_buy_nav)

  NOTE: If the PDF parsed a Closing Unit Balance, that value is stored as
  current_units on Portfolio rows and is used as the authoritative unit count.
  We detect this and prefer it over the computed sum.

  NOTE: folio_number is NOT part of the grouping key. Synthetic opening-balance
  rows have folio=None while real transaction rows have a folio — if we grouped
  by folio, each fund would appear twice. Folio is kept as metadata only.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Portfolio

logger = logging.getLogger(__name__)

PURCHASE_TYPES   = {"SIP", "lumpsum", "switch_in"}
REDEMPTION_TYPES = {"redemption", "switch_out"}


@dataclass
class HoldingRecord:
    fund_name:        str
    scheme_code:      Optional[str]
    folio_number:     Optional[str]

    # Unit accounting
    purchase_units:   float = 0.0
    redemption_units: float = 0.0
    current_units:    float = 0.0   # authoritative (from closing balance if available)

    # Amount accounting (always absolute / positive)
    invested_amount:  float = 0.0   # gross purchases only
    redeemed_amount:  float = 0.0   # gross redemption proceeds

    # Derived
    avg_buy_nav:      Optional[float] = None
    realized_gain:    float = 0.0

    # Timeline
    first_purchase:   Optional[date] = None
    last_transaction: Optional[date] = None

    # Valuation (filled by valuation.py)
    current_nav:      Optional[float] = None
    current_value:    float = 0.0
    unrealized_gain:  float = 0.0
    unrealized_pct:   float = 0.0
    daily_gain:       float = 0.0
    daily_gain_pct:   float = 0.0

    # Status
    is_fully_redeemed: bool = False


def reconstruct_holdings(
    db: Session,
    user_id: str,
) -> List[HoldingRecord]:
    """
    Reconstruct holdings from the portfolios table.

    Returns one HoldingRecord per (fund_name, scheme_code, folio_number) group.
    Groups with zero current units are still returned (is_fully_redeemed=True)
    unless ALL their rows come from redemptions only (e.g. legacy data).
    """
    # Single efficient query: all transactions for this user
    rows = (
        db.query(
            Portfolio.fund_name,
            Portfolio.scheme_code,
            Portfolio.folio_number,
            Portfolio.transaction_type,
            Portfolio.transaction_date,
            Portfolio.amount_inr,
            Portfolio.units,
            Portfolio.current_units,   # PDF-authoritative closing balance
        )
        .filter(Portfolio.user_id == user_id)
        .order_by(Portfolio.transaction_date.asc())
        .all()
    )

    # Group by (fund_name, scheme_code, folio_number)
    groups: Dict[tuple, HoldingRecord] = {}

    for (
        fund_name, scheme_code, folio_number,
        txn_type, txn_date, amount_inr, units, closing_units
    ) in rows:
        key = (fund_name, scheme_code or "")

        if key not in groups:
            groups[key] = HoldingRecord(
                fund_name=fund_name,
                scheme_code=scheme_code,
                folio_number=folio_number or None,
            )

        rec = groups[key]
        amt = abs(float(amount_inr)) if amount_inr is not None else 0.0
        u   = abs(float(units))      if units      is not None else 0.0

        if txn_type in PURCHASE_TYPES:
            rec.purchase_units  += u
            rec.invested_amount += amt
            if txn_date and (rec.first_purchase is None or txn_date < rec.first_purchase):
                rec.first_purchase = txn_date

        elif txn_type in REDEMPTION_TYPES:
            rec.redemption_units += u
            rec.redeemed_amount  += amt

        # Track latest transaction date
        if txn_date and (rec.last_transaction is None or txn_date > rec.last_transaction):
            rec.last_transaction = txn_date

        # PDF-authoritative closing balance: if present on ANY row for this group,
        # remember it — we'll use it as current_units (overrides computed sum).
        if closing_units is not None and float(closing_units) >= 0:
            # Use the max seen closing_units value (in case of multiple rows)
            rec.current_units = max(rec.current_units, float(closing_units))

    # Post-process each holding
    for rec in groups.values():
        # If no PDF closing balance was found, compute from transaction sums
        if rec.current_units == 0.0 and rec.purchase_units > 0:
            rec.current_units = max(0.0, rec.purchase_units - rec.redemption_units)

        # Average buy NAV
        if rec.purchase_units > 0:
            rec.avg_buy_nav = rec.invested_amount / rec.purchase_units

        # Realized gain: proceeds - (redeemed_units × avg_buy_nav)
        if rec.redemption_units > 0 and rec.avg_buy_nav:
            cost_of_redeemed = rec.redemption_units * rec.avg_buy_nav
            rec.realized_gain = rec.redeemed_amount - cost_of_redeemed

        # Mark fully redeemed
        rec.is_fully_redeemed = (rec.current_units <= 0.001)

    return list(groups.values())
