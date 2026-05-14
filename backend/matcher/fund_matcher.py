"""
Fund name → AMFI scheme code matcher using mfapi.in REST API.

Strategy per fund (tries in order, stops at first match):
  1. Full scheme name (e.g. "Parag Parikh Flexi Cap Fund Direct Plan Growth")
  2. Core scheme keywords (e.g. "Parag Parikh Flexi Cap")
  3. AMC short name (e.g. "PPFAS Mutual Fund")
  4. First 3–4 significant words
"""
import re
import logging
from typing import Optional, Dict, Any, List

import httpx

logger = logging.getLogger(__name__)

MFAPI_BASE = "https://api.mfapi.in/mf"

# Common noise words to strip before searching. NOTE: ISIN-like patterns
# ("INF879O01027", "INZ000208032") are handled by a separate case-sensitive
# regex below — including `inf\w+` here (with re.IGNORECASE) would also
# strip legitimate words like "Infrastructure", "Infosys", "Infinity".
_NOISE = re.compile(
    r"\b(direct|regular|growth|idcw|dividend|payout|reinvestment|plan|option|"
    r"non.?demat|demat|fund|instalment|online|bse|nse|isin|"
    r"advisor|formerly|series|sr)\b",
    re.IGNORECASE,
)

# ISIN codes are exactly INF + 9 alphanumerics (uppercase). Advisor codes are
# INZ + 9 alphanumerics. We strip these case-sensitively so we don't eat
# normal words that happen to start with "inf"/"inz".
_ISIN_LIKE = re.compile(r"\b(?:INF|INZ)[A-Z0-9]{9}\b")


def _clean(name: str) -> str:
    """Strip code prefixes, ISINs, and noise words."""
    # Remove leading scheme code like "PP001ZG-" (uppercase letters/digits)
    name = re.sub(r"^[A-Z0-9]{4,}-", "", name)
    # Remove ISIN block ("- ISIN: INF879O01027 ...")
    name = re.sub(r"\s*-\s*ISIN:\s*\S+.*$", "", name, flags=re.IGNORECASE)
    # Remove standalone ISIN / advisor codes (case-sensitive — uppercase only)
    name = _ISIN_LIKE.sub(" ", name)
    # Remove parenthetical notes
    name = re.sub(r"\(.*?\)", "", name)
    # Remove noise words
    name = _NOISE.sub(" ", name)
    # Drop stray leading/trailing punctuation/whitespace
    name = re.sub(r"[\s\-,]+$", "", name)
    name = re.sub(r"^[\s\-,]+", "", name)
    # Collapse whitespace
    return re.sub(r"\s+", " ", name).strip()


def _candidate_queries(scheme_name: str, amc_name: str) -> List[str]:
    """Generate ordered list of search queries, most specific first."""
    queries = []

    if scheme_name:
        # 1. Cleaned scheme name (most specific)
        cleaned = _clean(scheme_name)
        if cleaned:
            queries.append(cleaned)

        # 2. First 4 meaningful words of cleaned name
        words = [w for w in cleaned.split() if len(w) > 2]
        if len(words) >= 3:
            queries.append(" ".join(words[:4]))

        # 3. First 3 words
        if len(words) >= 3:
            queries.append(" ".join(words[:3]))

    # 4. AMC name fallback
    if amc_name:
        amc_clean = re.sub(r"\b(mutual fund|mf|asset management)\b", "", amc_name, flags=re.IGNORECASE).strip()
        if amc_clean:
            queries.append(amc_clean)

    # Deduplicate while preserving order
    seen, unique = set(), []
    for q in queries:
        q = q.strip()
        if q and q.lower() not in seen:
            seen.add(q.lower())
            unique.append(q)
    return unique


async def match_scheme_code(
    fund_name: str,
    scheme_name: str = "",
) -> Optional[str]:
    """
    Search mfapi.in for a scheme code.

    Args:
        fund_name:   Short AMC-level name, e.g. "PPFAS Mutual Fund"
        scheme_name: Full scheme string from PDF, e.g.
                     "PP001ZG-Parag Parikh Flexi Cap Fund - Direct Plan Growth"
    """
    candidates = _candidate_queries(scheme_name, fund_name)
    # Build the set of identifying tokens from the original scheme — used to
    # score multiple mfapi.in results and avoid picking near-namesake funds
    # (e.g. "Tata Digital India" vs "Tata Nifty Digital ETF Fund of Fund").
    target_tokens = _significant_tokens(_clean(scheme_name) if scheme_name else fund_name)
    logger.info(f"Matching '{fund_name}' with queries: {candidates} (target tokens: {target_tokens})")

    async with httpx.AsyncClient(timeout=15.0) as client:
        for query in candidates:
            result = await _search_api(client, query, target_tokens)
            if result:
                code = str(result["schemeCode"])
                logger.info(
                    f"✅ Matched '{fund_name}' → '{result.get('schemeName')}' "
                    f"(code {code}) via query: '{query}'"
                )
                return code

    logger.warning(f"❌ No mfapi.in match for: '{fund_name}' (scheme: '{scheme_name}')")
    return None


def _significant_tokens(text: str) -> List[str]:
    """Lowercase words >2 chars, excluding generic plan/type words."""
    generic = {
        "fund", "direct", "regular", "growth", "plan", "option", "scheme",
        "mutual", "mf", "the", "and", "for", "with", "from",
    }
    return [
        w for w in re.findall(r"[a-zA-Z]+", text.lower())
        if len(w) > 2 and w not in generic
    ]


def _score_result(scheme_name: str, target_tokens: List[str]) -> int:
    """How many of the target's identifying tokens appear in this candidate.
    Higher is better. Direct + Growth plans get a small bonus so they outrank
    Regular/IDCW variants when token overlap ties.
    """
    sname = scheme_name.lower()
    overlap = sum(1 for t in target_tokens if t in sname)
    bonus = 0
    if "direct" in sname:
        bonus += 1
    if "growth" in sname:
        bonus += 1
    # Penalty for derivative product types that shouldn't outrank the canonical
    # fund unless their tokens explicitly match.
    if "etf" in sname and "etf" not in target_tokens:
        bonus -= 3
    if "fund of fund" in sname and "fund of fund" not in " ".join(target_tokens):
        bonus -= 3
    return overlap * 10 + bonus


async def _search_api(
    client: httpx.AsyncClient,
    query: str,
    target_tokens: List[str],
) -> Optional[Dict[str, Any]]:
    """Call mfapi.in search and return the best-scoring result."""
    try:
        resp = await client.get(f"{MFAPI_BASE}/search", params={"q": query})
        resp.raise_for_status()
        results = resp.json()
        if not (isinstance(results, list) and len(results) > 0):
            return None

        # Score each candidate against the target scheme's identifying tokens.
        # Only fall back to the first result if NOTHING scored above zero.
        scored = sorted(
            results,
            key=lambda r: _score_result(r.get("schemeName", ""), target_tokens),
            reverse=True,
        )
        best = scored[0]
        best_score = _score_result(best.get("schemeName", ""), target_tokens)
        if best_score > 0:
            return best
        # No meaningful overlap — fall back to first Direct+Growth, then first
        for r in results:
            sname = r.get("schemeName", "").lower()
            if "direct" in sname and "growth" in sname:
                return r
        return results[0]
    except httpx.HTTPError as e:
        logger.error(f"mfapi.in search failed for '{query}': {e}")
    except Exception as e:
        logger.error(f"Unexpected error searching mfapi.in: {e}")
    return None


async def get_latest_nav(scheme_code: str) -> Optional[float]:
    """Get the latest NAV for a scheme code from mfapi.in."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{MFAPI_BASE}/{scheme_code}/latest")
            resp.raise_for_status()
            data = resp.json()
            if "data" in data and len(data["data"]) > 0:
                nav_str = data["data"][0].get("nav")
                if nav_str:
                    return float(nav_str)
    except httpx.HTTPError as e:
        logger.error(f"mfapi.in NAV fetch failed for {scheme_code}: {e}")
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse NAV for {scheme_code}: {e}")
    return None
