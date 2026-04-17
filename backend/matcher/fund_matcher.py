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

# Common noise words to strip before searching
_NOISE = re.compile(
    r"\b(direct|regular|growth|idcw|dividend|payout|reinvestment|plan|option|"
    r"non.?demat|demat|fund|instalment|online|bse|nse|isin|inf\w+|"
    r"advisor|inz\w+|formerly|non|series|sr)\b",
    re.IGNORECASE,
)


def _clean(name: str) -> str:
    """Strip code prefixes, ISINs, and noise words."""
    # Remove leading scheme code like "PP001ZG-"
    name = re.sub(r"^[A-Z0-9]{4,}-", "", name)
    # Remove ISIN block
    name = re.sub(r"\s*-\s*ISIN:\s*\S+.*$", "", name, flags=re.IGNORECASE)
    # Remove parenthetical notes
    name = re.sub(r"\(.*?\)", "", name)
    # Remove noise words
    name = _NOISE.sub(" ", name)
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
    logger.info(f"Matching '{fund_name}' with queries: {candidates}")

    async with httpx.AsyncClient(timeout=15.0) as client:
        for query in candidates:
            result = await _search_api(client, query)
            if result:
                code = str(result["schemeCode"])
                logger.info(
                    f"✅ Matched '{fund_name}' → '{result.get('schemeName')}' "
                    f"(code {code}) via query: '{query}'"
                )
                return code

    logger.warning(f"❌ No mfapi.in match for: '{fund_name}' (scheme: '{scheme_name}')")
    return None


async def _search_api(
    client: httpx.AsyncClient, query: str
) -> Optional[Dict[str, Any]]:
    """Call mfapi.in search and return the best result."""
    try:
        resp = await client.get(f"{MFAPI_BASE}/search", params={"q": query})
        resp.raise_for_status()
        results = resp.json()
        if isinstance(results, list) and len(results) > 0:
            # Prefer Direct plans when there are multiple
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
