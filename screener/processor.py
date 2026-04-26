import yfinance as yf
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import log, MIN_MCAP_CR, INFO_WORKERS
from .utils import normalise, pct_ret
from .finance import fetch_stock_data
from .cache import save_cache
from .calculations import price_n_days


def is_valid_ticker(t: dict) -> bool:
    """Filter out ETFs and Funds, and clean tickers."""
    tk = t.get("ticker", "").replace("$", "")
    t["ticker"] = tk
    name = t.get("company_name", "").upper()
    if not tk or not name:
        return False
    skip = ["ETF", "FUND", "GROWTH", "INSTITUTIONAL", "NIFTY", "SENSEX", "INDEX", "REIT", "INVIT"]
    if any(k in name for k in skip):
        return False
    if not (tk.endswith(".NS") or tk.endswith(".BO")):
        return False
    base = tk.rsplit(".", 1)[0]
    if tk.endswith(".BO") and not base.isdigit():
        return False
    if tk.endswith(".NS") and not base.replace("-", "").replace("&", "").isalnum():
        return False
    return True


def dedup_by_isin(tickers: list[dict]) -> list:
    """Keep NSE ticker if dual-listed (same ISIN)."""
    isin_to_nse, isin_to_bse, no_isin = {}, {}, []
    for t in tickers:
        isin = t.get("isin", "").strip()
        if not isin or isin == "nan":
            no_isin.append(t)
        elif t["exchange"] == "NSE":
            isin_to_nse[isin] = t
        else:
            isin_to_bse[isin] = t

    result = []
    for isin, nse_t in isin_to_nse.items():
        bse_t = isin_to_bse.get(isin)
        result.append({**nse_t, "bse_code": bse_t["bse_code"] if bse_t else "", "mkt_cap_cr": bse_t["mkt_cap_cr"] if bse_t else nse_t.get("mkt_cap_cr")})

    result.extend([t for isin, t in isin_to_bse.items() if isin not in isin_to_nse])
    seen = {t["ticker"] for t in result}
    for t in no_isin:
        if t["ticker"] not in seen:
            seen.add(t["ticker"]); result.append(t)
    return result


def filter_by_mcap(tickers: list, bhavcopy_prices: dict) -> list:
    """Filter out tickers below MIN_MCAP_CR."""
    if MIN_MCAP_CR <= 0: return tickers
    needs_mcap = [t for t in tickers if t.get("mkt_cap_cr") is None]
    direct_mcap = {}
    if needs_mcap:
        log.info(f"  Fetching market_cap for {len(needs_mcap)} tickers via Yahoo...")
        def get_mc(sym):
            try:
                fi = yf.Ticker(sym).fast_info
                return sym, round(getattr(fi, "market_cap", 0) / 1e7, 1)
            except: return sym, None
        with ThreadPoolExecutor(max_workers=INFO_WORKERS) as pool:
            futures = {pool.submit(get_mc, t["ticker"]): t for t in needs_mcap}
            for fut in as_completed(futures):
                s, mc = fut.result(); direct_mcap[s] = mc

    kept, dropped = [], 0
    for t in tickers:
        mc = t.get("mkt_cap_cr") or direct_mcap.get(t["ticker"])
        if mc is None:
            p, sh = bhavcopy_prices.get(t["ticker"]), t.get("shares_outstanding")
            if p and sh: mc = round((p * sh) / 1e7, 1)
        if mc and mc < MIN_MCAP_CR: dropped += 1
        else: kept.append({**t, "mkt_cap_cr": mc})
    log.info(f"MCap filter done: {len(kept)} kept | {dropped} below ₹{MIN_MCAP_CR} Cr")
    return kept


def fetch_all_stock_data_parallel(tickers: list[dict], price_data: dict, all_tickers: list) -> list:
    """Fetch per-stock data in parallel with Checkpoint Saving and RS calculation."""
    n = len(tickers)
    rows = [None] * n

    # 1. Fetch Benchmark (Nifty 50)
    log.info("Fetching Nifty 50 benchmark for RS calculation...")
    idx_ret = 0
    try:
        nifty = yf.download("^NSEI", period="1y", progress=False, auto_adjust=True)
        if not nifty.empty:
            c = normalise(nifty["Close"])
            cp = float(c.iloc[-1])
            p1y = price_n_days(c, 365)
            idx_ret = pct_ret(cp, p1y) or 0
            log.info(f"Nifty 50 1y Return: {idx_ret:.1f}%")
    except Exception as e:
        log.warning(f"Failed to fetch Nifty 50: {e}")

    def worker(idx: int, stock: dict):
        tk = stock["ticker"]
        cls = normalise(price_data.get(tk, {}).get("Close", pd.Series(dtype=float)))
        cp = round(float(cls.iloc[-1]), 2) if not cls.empty else None
        try:
            data = fetch_stock_data(stock, price_data, cp, index_return_1y=idx_ret)
            if data.get("MCap (Cr)") is None: data["MCap (Cr)"] = stock.get("mkt_cap_cr")
        except Exception as e:
            log.warning(f"fetch_stock_data failed for {tk}: {e}"); data = {}
        return idx, {"Ticker": tk, "Name": stock["company_name"], "ISIN": stock.get("isin", ""), **data}

    log.info(f"Fetching financials for {n} tickers ({INFO_WORKERS} workers)...")
    with ThreadPoolExecutor(max_workers=INFO_WORKERS) as pool:
        futures = {pool.submit(worker, i, t): i for i, t in enumerate(tickers)}
        done = 0
        for fut in as_completed(futures):
            try:
                i, r = fut.result(); rows[i] = r
            except: pass
            done += 1
            if done % 50 == 0 or done == n:
                log.info(f"  [{done}/{n}] complete. Saving checkpoint...")
                save_cache(all_tickers, update_tickers=False, update_shares=True)

    rows = [r for r in rows if r is not None]
    rows.sort(key=lambda x: x.get("Name", "").lower())
    return rows
