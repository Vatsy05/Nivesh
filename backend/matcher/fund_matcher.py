"""
Fund name → AMFI scheme code matcher using mfapi.in REST API.
"""
import logging
from typing import Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)

MFAPI_BASE = "https://api.mfapi.in/mf"


async def match_scheme_code(fund_name: str) -> Optional[str]:
    """
    Search mfapi.in for a mutual fund by name and return the scheme code.
    
    Strategy:
    1. Search with full fund name
    2. If no results, retry with first 4 words only
    3. If still no match, return None (flagged as 'unmatched')
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Attempt 1: full name
        result = await _search_api(client, fund_name)
        if result:
            return str(result["schemeCode"])

        # Attempt 2: first 4 words
        short_name = " ".join(fund_name.split()[:4])
        if short_name != fund_name:
            logger.info(f"Retrying mfapi.in search with: '{short_name}'")
            result = await _search_api(client, short_name)
            if result:
                return str(result["schemeCode"])

    logger.warning(f"No mfapi.in match for: '{fund_name}'")
    return None


async def _search_api(client: httpx.AsyncClient, query: str) -> Optional[Dict[str, Any]]:
    """Call mfapi.in search and return top result."""
    try:
        resp = await client.get(f"{MFAPI_BASE}/search", params={"q": query})
        resp.raise_for_status()
        results = resp.json()
        if isinstance(results, list) and len(results) > 0:
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
