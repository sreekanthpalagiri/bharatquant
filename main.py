import time
import os
from datetime import datetime
from screener.network import (
    download_nse_tickers,
    download_bse_bulk_mcap,
    load_nse_tickers,
    load_bse_bulk_mcap,
)
from screener.config import (
    log,
    TICKER_CACHE_FILE,
    TICKER_CACHE_DAYS,
    SHARES_CACHE_DAYS,
    COLUMNS,
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


def main():
    print("\n" + "=" * 65)
    print("              🇮🇳  BHARATQUANT PROFESSIONAL SCREENER  🇮🇳")
    print("=" * 65 + "\n")

    log.info("Starting BharatQuant Screener...")

    # 1. Tickers (14-day cache)
    all_tickers = load_cache()
    if not all_tickers:
        log.info("Downloading fresh ticker lists...")
        download_nse_tickers()
        download_bse_bulk_mcap()
        nse_raw = load_nse_tickers()
        bse_raw = load_bse_bulk_mcap()

        log.info("Merging and deduplicating...")
        merged = nse_raw + bse_raw
        valid = [t for t in merged if is_valid_ticker(t)]
        all_tickers = dedup_by_isin(valid)
        save_cache(all_tickers, update_tickers=True)

    # 2. Shares (14-day cache)
    needs_shares = [t for t in all_tickers if t.get("shares_outstanding") is None]
    if needs_shares:
        shares_map = fetch_shares_outstanding(needs_shares)
        for t in all_tickers:
            if t["ticker"] in shares_map:
                t["shares_outstanding"] = shares_map[t["ticker"]]
        save_cache(all_tickers, update_shares=True)

    # 3. Prices (Fresh daily)
    log.info("Downloading daily price batch (5y history)...")
    ticker_list = [t["ticker"] for t in all_tickers]
    price_data = {}
    for i in range(0, len(ticker_list), 100):
        batch = ticker_list[i : i + 100]
        price_data.update(fetch_prices_batch(batch))
        time.sleep(1.0)

    # 4. MCap Filter
    bhavcopy_prices = {
        tk: float(d["Close"].iloc[-1])
        for tk, d in price_data.items()
        if not d.get("Close", []).empty
    }
    filtered = filter_by_mcap(all_tickers, bhavcopy_prices)

    # 5. Financials (Parallel + Cache)
    rows = fetch_all_stock_data_parallel(filtered, price_data, all_tickers)

    # 6. Export
    write_excel(rows)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("\nStopped by user.")
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
