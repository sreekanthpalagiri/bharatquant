import os
import time

# Ensure pure Python implementation of Protobuf is used
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from screener.config import (
    log, MAX_STOCKS_PER_EXCHANGE, BATCH_SIZE, SLEEP_PRICE_BATCH,
    MIN_PRICE, WHITELIST
)
from screener.utils import clean_code
from screener.cache import (
    load_ticker_cache, shares_cache_fresh, save_cache
)
from screener.network import (
    get_nse_tickers, get_bse_tickers, fetch_bhavcopy_prices
)
from screener.finance import (
    fetch_shares_outstanding, fetch_prices_batch
)
from screener.processor import (
    dedup_by_isin, is_valid_ticker, filter_by_mcap, fetch_all_stock_data_parallel
)
from screener.exporter import write_excel

def main():
    log.info("=" * 65)
    log.info("NSE + BSE Full Screener → Excel")
    log.info("=" * 65)

    # ── Step 1: Ticker list (cached, refresh per TICKER_CACHE_DAYS) ─────
    all_tickers = load_ticker_cache()
    if all_tickers is None:
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

        log.info(f"Raw tickers after sanitise: {len(sanitised)} (NSE {len(nse)}, BSE {len(bse)})")
        all_tickers = dedup_by_isin(sanitised)
        save_cache(all_tickers, update_tickers=True, update_shares=False)

    if not all_tickers:
        log.error("No tickers. Check internet connection.")
        return

    # ── Step 2: Validity filter & Cleaning ────────────────────────────
    unique = [t for t in all_tickers if is_valid_ticker(t)]
    save_cache(all_tickers, update_tickers=True, update_shares=False)
    log.info(f"Master list cleaned: {len(unique)} valid stocks.")

    # ── Step 3: Bhavcopy prices (Smart Matching via ISIN) ───────────────
    log.info("Fetching today's closing prices from NSE + BSE bhavcopy...")
    bhavcopy_prices = fetch_bhavcopy_prices(unique)

    # ── Step 3.5: Penny Stock Shield ───────────────────────────────────
    # Mark penny stocks in the master list and filter them out of 'unique'
    penny_dropped = 0
    clean_unique = []
    
    for t in unique:
        tk = t["ticker"]
        price = bhavcopy_prices.get(tk)
        
        if price is not None:
            if price < MIN_PRICE and tk not in WHITELIST:
                t["penny_stock"] = "yes"
                penny_dropped += 1
                continue
            else:
                t["penny_stock"] = "no"
        else:
            t["penny_stock"] = "unknown"
            
        clean_unique.append(t)

    unique = clean_unique
    if penny_dropped > 0:
        log.info(f"Penny Stock Shield: Ignored {penny_dropped} stocks priced below ₹{MIN_PRICE} (Whitelisted: {len(WHITELIST)})")
        save_cache(all_tickers, update_tickers=False, update_shares=True)

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
                if tk in master_map:
                    master_map[tk]["shares_outstanding"] = shares
                populated_count += 1

    if populated_count > 0:
        log.info(f"Auto-calculated shares for {populated_count} tickers using local data.")
        save_cache(all_tickers, update_tickers=False, update_shares=True)

    # 5b. Identify remainders for Yahoo
    to_fetch = [t for t in unique if t.get("shares_outstanding") is None]

    if to_fetch:
        symbols_to_log = ", ".join([t["ticker"] for t in to_fetch[:10]])
        if len(to_fetch) > 10:
            symbols_to_log += f" (+{len(to_fetch)-10} more)"
        log.info(f"Still missing shares for {len(to_fetch)} tickers. Requesting from Yahoo: {symbols_to_log}")
        
        shares_map = fetch_shares_outstanding(to_fetch)
        for tk, val in shares_map.items():
            for t in unique:
                if t["ticker"] == tk:
                    t["shares_outstanding"] = val
                    break
            if tk in master_map:
                master_map[tk]["shares_outstanding"] = val
        
        save_cache(all_tickers, update_tickers=False, update_shares=True)
        log.info("Updated cache with Yahoo share data.")

    # ── Step 6: Full 5y price fetch for filtered tickers ─────────────────
    symbols  = [t["ticker"] for t in unique]
    price_data = {}
    total_b  = (len(symbols) + BATCH_SIZE - 1) // BATCH_SIZE
    log.info(f"Full 5y price fetch for {len(symbols)} tickers ({total_b} batches)...")
    for i in range(0, len(symbols), BATCH_SIZE):
        batch = symbols[i:i + BATCH_SIZE]
        log.info(f"Price batch {i//BATCH_SIZE+1}/{total_b}  ({len(batch)})...")
        price_data.update(fetch_prices_batch(batch))
        time.sleep(SLEEP_PRICE_BATCH)

    # ── Step 7: Parallel financials fetch (with Checkpoint Saving) ───────
    rows = fetch_all_stock_data_parallel(unique, price_data, all_tickers)
    save_cache(all_tickers, update_tickers=False, update_shares=True)

    # ── Step 8: Write Excel ───────────────────────────────────────────────
    write_excel(rows)

if __name__ == "__main__":
    main()
