"""
BharatQuant: Professional NSE + BSE Quantitative Stock Screener.

This script orchestrates the full end-to-end flow:
1. Downloads and caches ticker lists from NSE and BSE.
2. Fetches official Bhavcopy prices and applies the 'Penny Stock Shield'.
3. Performs 'Smart Population' of shares outstanding to minimize Yahoo API calls.
4. Filters stocks by Market Cap and price quality.
5. Performs deep financial analysis (Piotroski F-Score, YoY Growth).
6. Generates a color-coded Excel report for investment research.
"""

import time
import os
from datetime import datetime

# Mandatory fix for Protobuf on some systems
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from screener.network import (
    get_nse_tickers,
    get_bse_tickers,
    fetch_bhavcopy_prices,
    fetch_nse_pledge_data,
)
from screener.config import (
    log,
    TICKER_CACHE_FILE,
    TICKER_CACHE_DAYS,
    SHARES_CACHE_DAYS,
    MIN_PRICE,
    WHITELIST,
    SLEEP_PRICE_BATCH,
)
from screener.processor import (
    dedup_by_isin,
    filter_by_mcap,
    fetch_all_stock_data_parallel,
    is_valid_ticker,
)
from screener.finance import fetch_shares_outstanding, fetch_prices_batch
from screener.exporter import write_excel
from screener.cache import load_cache, save_cache
from screener.utils import clean_code


def main():
    """
    Main entry point for BharatQuant.
    Orchestrates the data pipeline with detailed progress logging.
    """
    print("\n" + "=" * 65)
    print("              🇮🇳  BHARATQUANT PROFESSIONAL SCREENER  🇮🇳")
    print("=" * 65 + "\n")

    log.info("Starting BharatQuant Screener...")

    # ── Step 1: Ticker list (cached, refresh per TICKER_CACHE_DAYS) ─────
    all_tickers = load_cache()
    if all_tickers is None:
        log.info("Downloading fresh ticker lists...")
        nse = get_nse_tickers()
        bse = get_bse_tickers()

        raw = nse + bse
        sanitised = []
        for t in raw:
            tk = t["ticker"]
            if tk.endswith(".BO"):
                base = clean_code(tk[:-3])
                if base.isdigit():
                    t = {**t, "ticker": base + ".BO", "bse_code": base}
                    sanitised.append(t)
            elif tk.endswith(".NS"):
                base = tk[:-3].strip()
                if base and base.replace("-","").replace("&","").isalnum():
                    sanitised.append(t)

        log.info(f"Sanitised list: {len(sanitised)} tickers (NSE {len(nse)}, BSE {len(bse)})")
        all_tickers = dedup_by_isin(sanitised)
        save_cache(all_tickers, update_tickers=True)

    if not all_tickers:
        log.error("No tickers found. Check internet connection.")
        return

    # ── Step 2: Validity filter & Cleaning ────────────────────────────
    unique = [t for t in all_tickers if is_valid_ticker(t)]
    log.info(f"Master list cleaned: {len(unique)} valid stocks.")

    # ── Step 3: Bhavcopy prices (Smart Matching via ISIN) ───────────────
    log.info("Fetching today's closing prices from NSE + BSE bhavcopy...")
    bhavcopy_prices = fetch_bhavcopy_prices(unique)

    # ── Step 3.2: Corporate Pledge Data (NSE) ──────────────────────────
    pledge_data = fetch_nse_pledge_data()

    # ── Step 3.5: Penny Stock Shield ───────────────────────────────────
    penny_dropped = 0
    clean_unique = []
    for t in unique:
        tk = t["ticker"]
        price = bhavcopy_prices.get(tk)
        if price is not None:
            if price < MIN_PRICE and tk not in WHITELIST:
                penny_dropped += 1
                continue
        clean_unique.append(t)

    if penny_dropped > 0:
        log.info(f"Penny Stock Shield: Ignored {penny_dropped} stocks priced below ₹{MIN_PRICE}")
    unique = clean_unique

    # ── Step 4: MCap filter (using bulk MCap from BSE where available) ────
    unique = filter_by_mcap(unique, bhavcopy_prices)

    if not unique:
        log.error("No tickers passed MCap filter.")
        return

    # ── Step 5: Shares outstanding (Smart Population) ────────────────────
    master_map = {t["ticker"]: t for t in all_tickers}
    populated_count = 0
    for t in unique:
        tk = t["ticker"]
        if t.get("shares_outstanding") is None:
            mc_cr = t.get("mkt_cap_cr")
            price = bhavcopy_prices.get(tk)
            if mc_cr and price and price > 0:
                shares = int((mc_cr * 1e7) / price)
                t["shares_outstanding"] = shares
                
                # IMPORTANT: Update the original master list so it saves to the cache
                if tk in master_map:
                    master_map[tk]["shares_outstanding"] = shares
                    
                populated_count += 1

    if populated_count > 0:
        log.info(f"Smart Population: Calculated shares for {populated_count} tickers using local data.")
        save_cache(all_tickers, update_shares=True)

    # 5b. Identify remainders for Yahoo
    to_fetch = [t for t in unique if t.get("shares_outstanding") is None]
    if to_fetch:
        symbols_to_log = ", ".join([t["ticker"] for t in to_fetch[:10]])
        if len(to_fetch) > 10:
            symbols_to_log += f" (+{len(to_fetch)-10} more)"
        log.info(f"Still missing shares for {len(to_fetch)} tickers. Requesting from Yahoo: {symbols_to_log}")
        
        info_map = fetch_shares_outstanding(to_fetch)
        for t in all_tickers:
            tk = t["ticker"]
            if tk in info_map:
                res = info_map[tk]
                if res["shares"]:
                    t["shares_outstanding"] = res["shares"]
                if res["mkt_cap"]:
                    t["mkt_cap_cr"] = round(res["mkt_cap"] / 1e7, 1)
        save_cache(all_tickers, update_shares=True)

    # ── Step 6: Full 5y price fetch for filtered tickers ─────────────────
    symbols = [t["ticker"] for t in unique]
    price_data = {}
    batch_size = 100
    total_b = (len(symbols) + batch_size - 1) // batch_size
    log.info(f"Full 5y price fetch for {len(symbols)} tickers ({total_b} batches)...")
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        log.info(f"Price History: Downloading batch {i//batch_size+1}/{total_b}...")
        price_data.update(fetch_prices_batch(batch))
        time.sleep(SLEEP_PRICE_BATCH)

    # ── Step 7: Parallel financials fetch (with Checkpoint Saving) ───────
    rows = fetch_all_stock_data_parallel(unique, price_data, all_tickers, pledge_data)
    save_cache(all_tickers, update_shares=True)

    # ── Step 8: Write Excel ───────────────────────────────────────────────
    write_excel(rows)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("\nStopped by user.")
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
       main()
    except KeyboardInterrupt:
        log.info("\nStopped by user.")
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
