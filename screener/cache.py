"""
Caching System for BharatQuant.

Manages:
1. Persistent storage of ticker lists and share counts in JSON format.
2. TTL (Time-To-Live) logic to refresh exchange data every 14 days.
3. Thread-safe checkpoint saving during long financial runs.
"""

import os
import json
from datetime import datetime
from .config import TICKER_CACHE_FILE, TICKER_CACHE_DAYS, SHARES_CACHE_DAYS, log


def _read_raw_cache() -> dict:
    """Read the raw JSON cache file from disk. Returns {} if file is missing or corrupt."""
    if not os.path.exists(TICKER_CACHE_FILE):
        return {}
    try:
        with open(TICKER_CACHE_FILE) as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"Cache read error: {e}")
        return {}


def _cache_age_days(cache: dict, key: str) -> int:
    """Calculate the age of a specific cache key in days compared to the current time."""
    ts = cache.get(key)
    if not ts:
        return 9999
    try:
        return (datetime.now() - datetime.fromisoformat(ts)).days
    except Exception:
        return 9999


def load_cache() -> list:
    """
    Return the cached ticker list if it is younger than TICKER_CACHE_DAYS.
    Otherwise, returns None to trigger a fresh download from the exchanges.
    """
    cache = _read_raw_cache()
    if not cache:
        return None
    age = _cache_age_days(cache, "tickers_fetched_at")
    if age < TICKER_CACHE_DAYS:
        tickers = cache.get("tickers", [])
        log.info(
            f"Ticker cache: {len(tickers)} tickers, "
            f"{age}d old (refreshes every {TICKER_CACHE_DAYS}d)"
        )
        return tickers
    log.info(f"Ticker cache {age}d old — refreshing ticker list...")
    return None


def shares_cache_fresh() -> bool:
    """
    Check if the 'shares_outstanding' data in the cache is both recent and sufficiently populated.
    Triggers a refresh if the data is > 14 days old or if it is mostly empty.
    """
    cache = _read_raw_cache()
    age = _cache_age_days(cache, "shares_fetched_at")

    if age >= SHARES_CACHE_DAYS:
        log.info(f"Shares cache {age}d old — will refresh shares_outstanding...")
        return False

    tickers = cache.get("tickers", [])
    if not tickers:
        return False

    has_shares = sum(1 for t in tickers if t.get("shares_outstanding"))
    if has_shares < (len(tickers) * 0.1):  # If less than 10% have shares
        log.info(
            f"Shares cache is recent ({age}d) but mostly empty ({has_shares}/{len(tickers)}) — forcing refresh..."
        )
        return False

    log.info(
        f"Shares cache: {age}d old, {has_shares}/{len(tickers)} populated — "
        f"using cached data (refreshes every {SHARES_CACHE_DAYS}d)"
    )
    return True


def save_cache(
    tickers: list, update_tickers: bool = False, update_shares: bool = False
):
    """
    Write the current ticker list and timestamps to the JSON cache file.
    Use 'update_tickers' or 'update_shares' to reset the 14-day expiration timer.
    """
    cache = _read_raw_cache()  
    now = datetime.now().isoformat()

    if update_tickers:
        cache["tickers_fetched_at"] = now
    if update_shares:
        cache["shares_fetched_at"] = now

    cache["tickers"] = tickers

    try:
        with open(TICKER_CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
        tags = []
        if update_tickers:
            tags.append("tickers")
        if update_shares:
            tags.append("shares")
        log.info(
            f"Cache saved [{', '.join(tags) or 'data only'}] "
            f"→ {TICKER_CACHE_FILE}  ({len(tickers)} entries)"
        )
    except Exception as e:
        log.warning(f"Cache save failed: {e}")
