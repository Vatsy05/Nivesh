"""
Portfolio blueprint — CRUD + NAV refresh with 4-hour caching.
"""
import uuid
import asyncio
import logging
from datetime import datetime, timedelta, date

from flask import Blueprint, request, jsonify
from sqlalchemy import func

from app.database import SessionLocal
from app.models import Portfolio, NavCache
from matcher.fund_matcher import match_scheme_code, get_latest_nav

logger = logging.getLogger(__name__)

portfolio_bp = Blueprint("portfolio", __name__)

CACHE_HOURS = 4


def _get_user_id():
    user_id = request.headers.get("X-User-Id", "").strip()
    if not user_id:
        return None
    return user_id


def _txn_to_dict(txn: Portfolio) -> dict:
    return {
        "id": str(txn.id),
        "document_id": str(txn.document_id) if txn.document_id else None,
        "fund_name": txn.fund_name,
        "scheme_code": txn.scheme_code,
        "folio_number": txn.folio_number,
        "account_holder_name": txn.account_holder_name,
        "transaction_type": txn.transaction_type,
        "transaction_date": txn.transaction_date.isoformat() if txn.transaction_date else None,
        "amount_inr": float(txn.amount_inr) if txn.amount_inr is not None else None,
        "units": float(txn.units) if txn.units is not None else None,
        "nav_at_transaction": float(txn.nav_at_transaction) if txn.nav_at_transaction is not None else None,
        "current_units": float(txn.current_units) if txn.current_units is not None else None,
        "scheme_match_status": txn.scheme_match_status or "matched",
        "created_at": txn.created_at.isoformat() if txn.created_at else None,
    }


# ── GET /portfolio ────────────────────────────────────────────────────────────

@portfolio_bp.get("/portfolio")
def get_portfolio():
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"detail": "Missing X-User-Id header"}), 401

    db = SessionLocal()
    try:
        _refresh_units(db, user_id)

        transactions = (
            db.query(Portfolio)
            .filter(Portfolio.user_id == user_id)
            .order_by(Portfolio.transaction_date.desc())
            .all()
        )

        return jsonify({
            "transactions": [_txn_to_dict(t) for t in transactions],
            "total_count": len(transactions),
        })
    finally:
        db.close()


# ── POST /portfolio/manual ────────────────────────────────────────────────────

@portfolio_bp.post("/portfolio/manual")
def add_manual_transaction():
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"detail": "Missing X-User-Id header"}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"detail": "Request body must be JSON"}), 400

    # Validate required fields
    required = ["fund_name", "transaction_type", "transaction_date"]
    for field in required:
        if not data.get(field):
            return jsonify({"detail": f"'{field}' is required"}), 400

    valid_types = {"SIP", "lumpsum", "redemption", "switch_in", "switch_out"}
    if data["transaction_type"] not in valid_types:
        return jsonify({"detail": f"Invalid type. Must be one of: {valid_types}"}), 400

    # Parse date
    try:
        txn_date = date.fromisoformat(data["transaction_date"])
    except ValueError:
        return jsonify({"detail": "Invalid transaction_date format, use YYYY-MM-DD"}), 400

    # Look up scheme code
    scheme_code = None
    match_status = "manual"
    try:
        scheme_code = asyncio.run(match_scheme_code(data["fund_name"]))
        match_status = "matched" if scheme_code else "unmatched"
    except Exception as e:
        logger.error(f"Scheme lookup failed: {e}")

    db = SessionLocal()
    try:
        txn = Portfolio(
            user_id=user_id,
            fund_name=data["fund_name"],
            scheme_code=data.get("scheme_code") or scheme_code,
            folio_number=data.get("folio_number"),
            account_holder_name=data.get("account_holder_name"),
            transaction_type=data["transaction_type"],
            transaction_date=txn_date,
            amount_inr=data.get("amount_inr"),
            units=data.get("units"),
            nav_at_transaction=data.get("nav_at_transaction"),
            scheme_match_status=match_status,
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)
        return jsonify(_txn_to_dict(txn)), 201
    except Exception as e:
        db.rollback()
        logger.error(f"Add manual transaction error: {e}")
        return jsonify({"detail": "Internal server error"}), 500
    finally:
        db.close()


# ── PATCH /portfolio/<id> ─────────────────────────────────────────────────────

@portfolio_bp.patch("/portfolio/<transaction_id>")
def update_transaction(transaction_id: str):
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"detail": "Missing X-User-Id header"}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"detail": "Request body must be JSON"}), 400

    db = SessionLocal()
    try:
        txn = db.query(Portfolio).filter(
            Portfolio.id == transaction_id,
            Portfolio.user_id == user_id,
        ).first()

        if not txn:
            return jsonify({"detail": "Transaction not found"}), 404

        # Re-match scheme code if fund_name changed
        if "fund_name" in data and data["fund_name"]:
            try:
                new_code = asyncio.run(match_scheme_code(data["fund_name"]))
                data["scheme_code"] = new_code
                data["scheme_match_status"] = "matched" if new_code else "unmatched"
            except Exception:
                data["scheme_match_status"] = "unmatched"

        # Parse date if present
        if "transaction_date" in data and isinstance(data["transaction_date"], str):
            try:
                data["transaction_date"] = date.fromisoformat(data["transaction_date"])
            except ValueError:
                return jsonify({"detail": "Invalid transaction_date format"}), 400

        allowed = {
            "fund_name", "scheme_code", "folio_number", "account_holder_name",
            "transaction_type", "transaction_date", "amount_inr", "units",
            "nav_at_transaction", "scheme_match_status",
        }
        for key, val in data.items():
            if key in allowed and val is not None:
                setattr(txn, key, val)

        db.commit()
        db.refresh(txn)
        return jsonify(_txn_to_dict(txn))
    except Exception as e:
        db.rollback()
        logger.error(f"Update transaction error: {e}")
        return jsonify({"detail": "Internal server error"}), 500
    finally:
        db.close()


# ── DELETE /portfolio/<id> ────────────────────────────────────────────────────

@portfolio_bp.delete("/portfolio/<transaction_id>")
def delete_transaction(transaction_id: str):
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"detail": "Missing X-User-Id header"}), 401

    db = SessionLocal()
    try:
        txn = db.query(Portfolio).filter(
            Portfolio.id == transaction_id,
            Portfolio.user_id == user_id,
        ).first()

        if not txn:
            return jsonify({"detail": "Transaction not found"}), 404

        db.delete(txn)
        db.commit()
        return jsonify({"message": "Transaction deleted"})
    except Exception as e:
        db.rollback()
        logger.error(f"Delete transaction error: {e}")
        return jsonify({"detail": "Internal server error"}), 500
    finally:
        db.close()


# ── NAV Refresh helpers ───────────────────────────────────────────────────────

def _refresh_units(db, user_id: str) -> None:
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
        cached = db.query(NavCache).filter(NavCache.scheme_code == scheme_code).first()
        if cached and cached.last_refreshed:
            if datetime.utcnow() - cached.last_refreshed < timedelta(hours=CACHE_HOURS):
                _update_net_units(db, user_id, scheme_code, purchase_types, redemption_types)
                continue

        try:
            nav = asyncio.run(get_latest_nav(scheme_code))
            if nav is not None:
                if cached:
                    cached.current_nav = nav
                    cached.last_refreshed = datetime.utcnow()
                else:
                    db.add(NavCache(
                        scheme_code=scheme_code,
                        current_nav=nav,
                        last_refreshed=datetime.utcnow(),
                    ))
                db.flush()
        except Exception as e:
            logger.error(f"NAV refresh failed for {scheme_code}: {e}")

        _update_net_units(db, user_id, scheme_code, purchase_types, redemption_types)

    db.commit()


def _update_net_units(db, user_id: str, scheme_code: str, purchase_types: set, redemption_types: set):
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
