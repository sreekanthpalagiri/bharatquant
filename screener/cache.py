import os
import json
from datetime import datetime
from .config import TICKER_CACHE_FILE, TICKER_CACHE_DAYS, SHARES_CACHE_DAYS, log


def _read_raw_cache() -> dict:
    """Read raw cache JSON. Returns {} on any error."""
    if not os.path.exists(TICKER_CACHE_FILE):
        return {}
    try:
        with open(TICKER_CACHE_FILE) as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"Cache read error: {e}")
        return {}


def _cache_age_days(cache: dict, key: str) -> int:
    """Return age in days of a timestamp key, or 9999 if missing."""
    ts = cache.get(key)
    if not ts:
        return 9999
    try:
        return (datetime.now() - datetime.fromisoformat(ts)).days
    except Exception:
        return 9999


def load_ticker_cache() -> list:
    """Return cached ticker list if fresh, else None."""
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
    """Return True if shares_outstanding in cache is fresh AND populated."""
    cache = _read_raw_cache()
    age = _cache_age_days(cache, "shares_fetched_at")

    if age >= SHARES_CACHE_DAYS:
        log.info(f"Shares cache {age}d old — will refresh shares_outstanding...")
        return False

    tickers = cache.get("tickers", [])
    if not tickers:
        return False

    # Check if we actually have data, not just nulls
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
    Save ticker list to cache.
    """
    cache = _read_raw_cache()  # preserve existing timestamps
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
