"""
Networking and Exchange Scraper Module for BharatQuant.

Handles:
1. Downloading ticker lists from NSE (CSV) and BSE (API).
2. Fetching daily Bhavcopy files for both exchanges.
3. ISIN-based smart matching to align prices across multiple exchanges.
"""

import io
import os
import time
import zipfile
import pandas as pd
from datetime import datetime, timedelta
from .config import TODAY, log, DATA_DIR, MAX_STOCKS_PER_EXCHANGE
from .utils import SESSION, clean_code


def get_last_trading_day(base_date: datetime) -> datetime:
    """
    Return the nearest weekday (Mon-Fri) on or before base_date.
    Used for locating the most recent Bhavcopy file.
    """
    d = base_date
    while d.weekday() > 4:
        d -= timedelta(days=1)
    return d


def is_stock(name: str, ticker: str) -> bool:
    """
    Basic check to exclude ETFs, Funds, and Indices from the processing list.
    Filters by keywords like 'ETF', 'FUND', 'NIFTY', etc.
    """
    name = str(name).upper()
    ticker = str(ticker).upper()
    skip = [
        "ETF",
        "FUND",
        "GROWTH",
        "INSTITUTIONAL",
        "NIFTY",
        "SENSEX",
        "INDEX",
        "REIT",
        "INVIT",
    ]
    if any(k in name for k in skip):
        return False
    return True


def clean_sym(sym: str) -> str:
    """Remove $ and other special characters from exchange symbols."""
    return str(sym).strip().replace("$", "")


def get_nse_tickers() -> list:
    """
    Fetch the master list of all listed equity symbols from the NSE archive.
    Saves a raw copy for audit purposes in the data directory.
    """
    log.info("Fetching NSE ticker list...")
    SESSION.get("https://www.nseindia.com", timeout=10)
    time.sleep(0.5)

    url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
    try:
        r = SESSION.get(url, timeout=20)
        if r.status_code == 200:
            raw_path = os.path.join(DATA_DIR, "nse_ticker_list.csv")
            with open(raw_path, "wb") as f:
                f.write(r.content)
            log.info(f"NSE Raw List Saved: {raw_path}")

            df = pd.read_csv(io.BytesIO(r.content))
            df.columns = df.columns.str.strip()
            out = []
            for _, row in df.iterrows():
                raw_sym = str(row.get("SYMBOL", "")).strip()
                sym = clean_sym(raw_sym)
                name = str(row.get("NAME OF COMPANY", sym)).strip()
                isin = str(row.get("ISIN NUMBER", "")).strip()
                if sym and is_stock(name, sym):
                    out.append(
                        {
                            "company_name": name,
                            "ticker": sym + ".NS",
                            "nse_code": sym,
                            "bse_code": "",
                            "isin": isin,
                            "exchange": "NSE",
                        }
                    )
            if MAX_STOCKS_PER_EXCHANGE and len(out) > MAX_STOCKS_PER_EXCHANGE:
                out = out[:MAX_STOCKS_PER_EXCHANGE]
            log.info(f"NSE (archive CSV): {len(out)} tickers")
            return out
    except Exception as e:
        log.warning(f"NSE source failed: {e}")
    return []


def get_bse_tickers() -> list:
    """
    Fetch the master list of all active equity scrips from the BSE API.
    This call is especially valuable as it provides bulk Market Cap data.
    """
    log.info("Fetching BSE ticker list...")
    try:
        r = SESSION.get(
            "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
            "?Group=&Scripcode=&industry=&segment=Equity&status=Active",
            headers={"Referer": "https://www.bseindia.com/"},
            timeout=25,
        )
        if r.status_code == 200:
            raw_path = os.path.join(DATA_DIR, "bse_bulk_mcap.json")
            with open(raw_path, "wb") as f:
                f.write(r.content)
            log.info(f"BSE Raw List Saved: {raw_path}")

            data = r.json()
            rows = data.get("Table", data) if isinstance(data, dict) else data
            out = []
            for item in rows:
                code = clean_code(item.get("SCRIP_CD", ""))
                name = str(item.get("Scrip_Name", "")).strip()
                isin = str(item.get("ISIN_NUMBER", "")).strip()
                mc = item.get("Mktcap")
                try:
                    mcap_cr = float(str(mc).replace(",", "")) if mc else None
                except:
                    mcap_cr = None

                if code and code.isdigit() and is_stock(name, code):
                    out.append(
                        {
                            "company_name": name,
                            "ticker": code + ".BO",
                            "nse_code": "",
                            "bse_code": code,
                            "isin": isin,
                            "exchange": "BSE",
                            "mkt_cap_cr": mcap_cr,
                        }
                    )
            if MAX_STOCKS_PER_EXCHANGE and len(out) > MAX_STOCKS_PER_EXCHANGE:
                out = out[:MAX_STOCKS_PER_EXCHANGE]
            log.info(f"BSE source: JSON API → {len(out)} tickers (including bulk MCap)")
            return out
    except Exception as e:
        log.warning(f"BSE API failed: {e}")
    return []


def fetch_bhavcopy_prices(all_tickers: list) -> dict:
    """
    Download and process the latest closing prices from both NSE and BSE.
    Uses ISIN-based matching to ensure that scrips listed on both exchanges 
    receive the most accurate daily price data available.
    """
    prices = {}
    isin_map = {}
    for t in all_tickers:
        isin = t.get("isin")
        if isin:
            isin_map.setdefault(isin, []).append(t["ticker"])

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    }

    def apply_row(row, code_col, isin_col, close_col, exchange_suffix):
        nonlocal prices
        count = 0
        try:
            p = float(str(row[close_col]).replace(",", ""))
            if p <= 0:
                return 0

            isin = str(row.get(isin_col, "")).strip()
            if isin and isin in isin_map:
                for tk in isin_map[isin]:
                    if tk not in prices:
                        prices[tk] = p
                        count += 1

            code = clean_code(row[code_col])
            if code:
                tk = f"{code}{exchange_suffix}"
                if tk not in prices:
                    prices[tk] = p
                    count += 1
        except:
            pass
        return count

    # ── NSE bhavcopy ─────────────────────────────────────────────────────
    for days_back in range(4):
        d = TODAY - timedelta(days=days_back)
        ds_yyyy = d.strftime("%Y%m%d")
        url_cm = f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{ds_yyyy}_F_0000.csv.zip"
        try:
            r = SESSION.get(
                url_cm,
                headers={"Referer": "https://www.nseindia.com/", **HEADERS},
                timeout=15,
            )
            if r.status_code == 200 and b"PK\x03\x04" in r.content[:10]:
                z = zipfile.ZipFile(io.BytesIO(r.content))
                csv_name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
                content = z.read(csv_name)
                df = pd.read_csv(io.BytesIO(content), dtype=str)
                save_path = os.path.join(DATA_DIR, f"nse_bhavcopy_{ds_yyyy}.xlsx")
                df.to_excel(save_path, index=False)
                log.info(f"NSE Raw File Saved (Excel): {save_path}")

                df.columns = df.columns.str.strip()
                code_col = next((c for c in df.columns if c.upper() in ("TCKRSYMB", "SYMBOL")), None)
                isin_col = next((c for c in df.columns if c.upper() == "ISIN"), None)
                close_col = next((c for c in df.columns if c.upper() in ("CLSPRIC", "CLOSE_PRICE", "CLOSE")), None)

                if code_col and close_col:
                    added = 0
                    for _, row in df.iterrows():
                        added += apply_row(row, code_col, isin_col, close_col, ".NS")
                    log.info(f"NSE (CM) prices added for {d.strftime('%d-%b-%Y')}: {added}")
                    break
        except: pass

    # ── BSE bhavcopy ─────────────────────────────────────────────────────
    for days_back in range(4):
        d = TODAY - timedelta(days=days_back)
        ds_yyyy = d.strftime("%Y%m%d")
        url_cm = f"https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_{ds_yyyy}_F_0000.CSV"
        try:
            r = SESSION.get(url_cm, headers={"Referer": "https://www.bseindia.com/", **HEADERS}, timeout=15)
            if r.status_code == 200:
                df = pd.read_csv(io.BytesIO(r.content), dtype=str)
                save_path = os.path.join(DATA_DIR, f"bse_bhavcopy_{ds_yyyy}.xlsx")
                df.to_excel(save_path, index=False)
                log.info(f"BSE Raw File Saved (Excel): {save_path}")

                df.columns = df.columns.str.strip()
                code_col = next((c for c in df.columns if c.upper() in ("FININSTRMID", "SC_CODE", "SCRIP_CD", "CODE")), None)
                isin_col = next((c for c in df.columns if c.upper() == "ISIN"), None)
                close_col = next((c for c in df.columns if c.upper() in ("CLSPRIC", "CLOSE_PRICE", "CLOSE")), None)

                if code_col and close_col:
                    added = 0
                    for _, row in df.iterrows():
                        added += apply_row(row, code_col, isin_col, close_col, ".BO")
                    log.info(f"BSE (CM) prices added for {d.strftime('%d-%b-%Y')}: {added}")
                    break
        except: pass

    log.info(f"Bhavcopy total: {len(prices)} unique closing prices loaded")
    return prices
