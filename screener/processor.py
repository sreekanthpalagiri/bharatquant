"""
Core Processing Engine for BharatQuant.

Handles:
1. Cross-exchange deduplication using ISINs.
2. Market Cap and Penny Stock filtering.
3. Parallel execution of financial data fetching to optimize performance.
4. Checkpoint saving to prevent data loss during long runs.
"""

import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import log, INFO_WORKERS, MIN_MCAP_CR, MIN_PRICE, WHITELIST
from .finance import fetch_stock_data
from .cache import save_cache
from .utils import normalise, pct_ret
from .calculations import price_n_days


def is_valid_ticker(t: dict) -> bool:
    """
    Validation check for scrip codes and symbols.
    Ensures NSE symbols are alphanumeric and BSE codes are digits.
    """
    tk = str(t.get("ticker", ""))
    if not (tk.endswith(".NS") or tk.endswith(".BO")):
        return False
        
    base = tk.rsplit(".", 1)[0]
    
    if tk.endswith(".BO") and not base.isdigit():
        return False
        
    if tk.endswith(".NS") and not base.replace("-", "").replace("&", "").isalnum():
        return False
        
    return True


def dedup_by_isin(tickers: list) -> list:
    """
    Deduplicate stocks across NSE and BSE using their unique ISIN.
    If a stock is on both exchanges, the NSE version is preferred as the primary ticker,
    but it merges the critical 'mkt_cap_cr' and 'bse_code' from the BSE record.
    Stocks without an ISIN are safely preserved and deduplicated by their Ticker.
    """
    log.info(f"Deduplicating {len(tickers)} tickers by ISIN...")
    isin_to_nse, isin_to_bse, no_isin = {}, {}, []
    
    for t in tickers:
        isin = str(t.get("isin", "")).strip()
        if not isin or isin == "nan":
            no_isin.append(t)
        elif t["exchange"] == "NSE":
            isin_to_nse[isin] = t
        else:
            isin_to_bse[isin] = t

    result = []
    # 1. Merge cross-listed stocks (Prefer NSE, pull MCap/Code from BSE)
    for isin, nse_t in isin_to_nse.items():
        bse_t = isin_to_bse.get(isin)
        merged = {
            **nse_t, 
            "bse_code": bse_t["bse_code"] if bse_t else "", 
            "mkt_cap_cr": bse_t["mkt_cap_cr"] if bse_t else nse_t.get("mkt_cap_cr")
        }
        result.append(merged)

    # 2. Add standalone BSE stocks
    result.extend([t for isin, t in isin_to_bse.items() if isin not in isin_to_nse])
    
    # 3. Add stocks without an ISIN (deduplicated by Ticker)
    seen = {t["ticker"] for t in result}
    for t in no_isin:
        if t["ticker"] not in seen:
            seen.add(t["ticker"])
            result.append(t)
            
    log.info(f"Unique stocks found: {len(result)}")
    return result


def filter_by_mcap(tickers: list, bhavcopy_prices: dict) -> list:
    """
    Filter out tickers below MIN_MCAP_CR.
    Fetches missing MCap via Yahoo fast_info for NSE-only stocks to ensure accurate filtering.
    """
    if MIN_MCAP_CR <= 0: return tickers
    needs_mcap = [t for t in tickers if t.get("mkt_cap_cr") is None]
    direct_mcap = {}
    if needs_mcap:
        log.info(f"Fetching market_cap for {len(needs_mcap)} tickers via Yahoo to ensure accurate filtering...")
        def get_mc(sym):
            try:
                fi = yf.Ticker(sym).fast_info
                return sym, round(getattr(fi, "market_cap", 0) / 1e7, 1)
            except: return sym, None
            
        with ThreadPoolExecutor(max_workers=INFO_WORKERS) as pool:
            futures = {pool.submit(get_mc, t["ticker"]): t for t in needs_mcap}
            for fut in as_completed(futures):
                s, mc = fut.result()
                if mc: direct_mcap[s] = mc

    kept, dropped = [], 0
    for t in tickers:
        mc = t.get("mkt_cap_cr") or direct_mcap.get(t["ticker"])
        if mc is None:
            # Try to calculate it if we have price and shares already
            p, sh = bhavcopy_prices.get(t["ticker"]), t.get("shares_outstanding")
            if p and sh: 
                mc = round((p * sh) / 1e7, 1)
                
        # Modify the original dictionary in-place so cache saving works
        t["mkt_cap_cr"] = mc
        
        if mc and mc < MIN_MCAP_CR: 
            dropped += 1
        else: 
            kept.append(t)
            
    log.info(f"MCap filter done: {len(kept)} kept | {dropped} below ₹{MIN_MCAP_CR} Cr")
    return kept


def fetch_all_stock_data_parallel(filtered_tickers: list, price_data: dict, all_tickers: list, pledge_data: dict = None) -> list:
    """
    Perform deep financial and technical analysis in parallel.
    Uses ThreadPoolExecutor to handle concurrent Yahoo Finance fetches.
    Saves a checkpoint every 50 stocks to ensure data is preserved.
    """
    if pledge_data is None: pledge_data = {}
    log.info(f"Starting deep analysis for {len(filtered_tickers)} stocks ({INFO_WORKERS} workers)...")
    results = []

    # 1. Fetch Benchmark (Nifty 50) for RS Score calculation
    log.info("Fetching Nifty 50 benchmark for RS calculation...")
    idx_ret = 0
    try:
        nifty = yf.download("^NSEI", period="1y", progress=False, auto_adjust=True)
        if not nifty.empty:
            c = normalise(nifty["Close"])
            val = c.iloc[-1]
            cp = float(val.item() if isinstance(val, pd.Series) else val)
            p1y = price_n_days(c, 365)
            idx_ret = pct_ret(cp, p1y) or 0
            log.info(f"Nifty 50 1y Return: {idx_ret:.1f}%")
    except Exception as e:
        log.warning(f"Failed to fetch Nifty 50: {e}")
    
    with ThreadPoolExecutor(max_workers=INFO_WORKERS) as pool:
        futures = {
            pool.submit(fetch_stock_data, t, price_data, None, idx_ret, pledge_data): t 
            for t in filtered_tickers
        }
        
        count = 0
        for fut in as_completed(futures):
            try:
                res = fut.result()
                if res:
                    results.append(res)
                    count += 1
                    
                    # Checkpoint saving every 50 stocks
                    if count % 50 == 0:
                        log.info(f"Progress Checkpoint: {count}/{len(filtered_tickers)} analyzed...")
                        save_cache(all_tickers, update_shares=True)
            except Exception as e:
                log.warning(f"Worker failed for a stock: {e}")

    log.info(f"Analysis complete. Total rows generated: {len(results)}")
    return results
