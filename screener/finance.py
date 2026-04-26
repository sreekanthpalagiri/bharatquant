"""
Financial Analysis and Metric Extraction Module for BharatQuant.

Handles:
1. Fetching Balance Sheets, Cash Flows, and Income Statements from Yahoo Finance.
2. Calculating the Piotroski F-Score (0-9 scale) for quality assessment.
3. Extracting YoY Quarterly Sales and Profit Growth percentages.
4. Managing a 14-day financial cache to speed up repeated runs.
"""

import time
import random
import pandas as pd
import yfinance as yf
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import log, INFO_WORKERS, TODAY, FINANCIALS_CACHE_DAYS
from .utils import sf, normalise, pct_ret
from .calculations import (
    price_n_days,
    calc_rsi,
    rolling_vol,
    dma_n,
    get_trend_signal,
    quarterly_flags,
    calc_piotroski_score,
)


def fetch_prices_batch(batch: list[str], attempt=0) -> dict:
    """
    Download up to 5 years of daily Close and Volume data for a batch of tickers.
    Includes exponential backoff and retry logic to handle Yahoo Finance rate limits.
    """
    if not batch:
        return {}
    try:
        raw = yf.download(
            " ".join(batch),
            period="5y",
            interval="1d",
            progress=False,
            auto_adjust=True,
            threads=False,
            timeout=30,
        )
        if raw.empty:
            return {}
        result = {}
        for col_type in ["Close", "Volume"]:
            if col_type not in raw.columns:
                continue
            block = raw[col_type]
            if isinstance(block, pd.Series):
                tk = batch[0]
                if tk not in result:
                    result[tk] = {}
                s = normalise(block.dropna())
                result[tk][col_type] = s
            else:
                for tk in batch:
                    if tk in block.columns:
                        s = normalise(block[tk].dropna())
                        if s.empty:
                            continue
                        if tk not in result:
                            result[tk] = {}
                        result[tk][col_type] = s
        return result
    except Exception as e:
        err = str(e).lower()
        if any(k in err for k in ["rate limit", "too many requests", "429", "unauthorized", "crumb"]):
            if attempt < 3:
                wait = 30 * (attempt + 1)
                log.warning(f"Yahoo error ({err}). Waiting {wait}s before retry {attempt+1}/3...")
                time.sleep(wait)
                return fetch_prices_batch(batch, attempt + 1)
        if len(batch) > 1:
            result = {}
            for tk in batch:
                result.update(fetch_prices_batch([tk], attempt))
                time.sleep(0.5)
            return result
        return {}


def fetch_shares_outstanding(tickers: list) -> dict:
    """
    Fetch shares_outstanding and marketCap for a list of tickers via parallel .info calls.
    Used as a fallback when 'Smart Population' in main.py cannot calculate shares.
    """
    n = len(tickers)
    log.info(f"Fetching missing data for {n} tickers from Yahoo ({INFO_WORKERS} workers)...")

    def get_info(stock):
        sym = stock["ticker"]
        time.sleep(random.uniform(0.1, 1.0))
        for attempt in range(2):
            try:
                ticker = yf.Ticker(sym)
                info = ticker.info
                if info:
                    so = info.get("sharesOutstanding")
                    mc = info.get("marketCap")
                    
                    # Also try to calculate shares if MCap exists but shares doesn't
                    if not so and mc:
                        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
                        if price and price > 0:
                            so = int(mc / price)
                            
                    if so or mc:
                        return sym, so, mc
            except Exception:
                pass
        return sym, None, None

    result = {}
    with ThreadPoolExecutor(max_workers=INFO_WORKERS) as pool:
        futures = {pool.submit(get_info, t): t["ticker"] for t in tickers}
        for fut in as_completed(futures):
            sym, shares, mcap = fut.result()
            if shares or mcap:
                result[sym] = {"shares": shares, "mkt_cap": mcap}
    return result


def fetch_stock_data(stock: dict, price_data: dict, cp: float, index_return_1y: float = 0.0) -> dict:
    """
    Perform deep analysis on a single stock.
    Combines cached financial data with fresh technical signals.
    Calculates: RS Score, F-Score, Trend, Growth %, Valuation Multiples, etc.
    """
    ticker_sym = stock["ticker"]
    pd_s = price_data.get(ticker_sym, {})
    close = normalise(pd_s.get("Close", pd.Series(dtype=float)))
    volume = normalise(pd_s.get("Volume", pd.Series(dtype=float)))

    if cp is None and not close.empty:
        cp = round(float(close.iloc[-1]), 2)

    # 1. Financial Cache Management
    cache = stock.get("financials_cache")
    is_fresh = False
    if cache:
        ts = cache.get("timestamp")
        if ts:
            dt = datetime.fromisoformat(ts)
            if (datetime.now() - dt).days < FINANCIALS_CACHE_DAYS:
                is_fresh = True

    if is_fresh:
        info = cache.get("info", {})
        roe3y = cache.get("roe3y")
        growth = cache.get("growth", {})
        f_score = cache.get("f_score")
    else:
        # Fetch fresh deep financials
        info = {}
        roe3y = None
        growth = {}
        f_score = None
        try:
            yt = yf.Ticker(ticker_sym)
            info = yt.info or {}
            
            # Annual Quality Stats (ROE 3y)
            af = yt.financials
            bs = yt.balance_sheet
            cf = yt.cashflow
            
            se_r = ni_r = None
            if not af.empty:
                for l in ["Stockholders Equity", "Total Stockholder Equity", "Common Stock Equity"]:
                    if l in af.index: se_r = af.loc[l]; break
                for l in ["Net Income", "Net Income Common Stockholders"]:
                    if l in af.index: ni_r = af.loc[l]; break
                if se_r is not None and ni_r is not None:
                    roes = [sf(ni_r[c]) / sf(se_r[c]) * 100 for c in af.columns[:3] if sf(ni_r[c]) and sf(se_r[c]) and sf(se_r[c]) != 0]
                    roe3y = round(sum(roes) / len(roes), 1) if roes else None
            
            # Piotroski F-Score calculation
            f_score = calc_piotroski_score(af, bs, cf)
            
            # Quarterly Growth (YoY)
            qf = yt.quarterly_financials
            if qf is not None and not qf.empty:
                rev_lbl = next((l for l in ["Total Revenue", "Operating Revenue"] if l in qf.index), None)
                ni_lbl = next((l for l in ["Net Income", "Net Income Common Stockholders"] if l in qf.index), None)
                if rev_lbl and len(qf.columns) >= 5:
                    cur_rev, old_rev = sf(qf.loc[rev_lbl].iloc[0]), sf(qf.loc[rev_lbl].iloc[4])
                    if cur_rev and old_rev: growth["Sales Growth % (YoY)"] = round((cur_rev / old_rev - 1) * 100, 1)
                if ni_lbl and len(qf.columns) >= 5:
                    cur_ni, old_ni = sf(qf.loc[ni_lbl].iloc[0]), sf(qf.loc[ni_lbl].iloc[4])
                    if cur_ni and old_ni: growth["Profit Growth % (YoY)"] = round((cur_ni / old_ni - 1) * 100, 1)

            stock["financials_cache"] = {
                "timestamp": datetime.now().isoformat(),
                "info": info,
                "roe3y": roe3y,
                "growth": growth,
                "f_score": f_score
            }
        except: pass

    # 2. Technical Data (Always Fresh)
    p1y = price_n_days(close, 365)
    ret1y = pct_ret(cp, p1y)
    rs_score = round(ret1y - index_return_1y, 1) if (ret1y is not None) else None
    dma50 = dma_n(close, 50)
    dma200 = dma_n(close, 200)
    trend = get_trend_signal(cp, dma50, dma200)

    # 3. Financial Metric Extraction
    def to_cr(v): return round(float(v) / 1e7, 0) if v else None
    mkt_cap = sf(info.get("marketCap"))
    mcap_cr = to_cr(mkt_cap)
    eps = sf(info.get("trailingEps"))
    bvps = sf(info.get("bookValue"))
    de = sf(info.get("debtToEquity"))
    
    r1 = sf(info.get("returnOnEquity"))
    roe1y = round(r1 * 100, 1) if r1 is not None else None
    
    om = sf(info.get("operatingMargins"))
    opm = round(om * 100, 1) if om is not None else None
    
    op_cf = to_cr(sf(info.get("operatingCashflow")))
    pe = sf(info.get("trailingPE")) or (round(cp / eps, 1) if (cp and eps and eps > 0) else None)
    pb = sf(info.get("priceToBook")) or (round(cp / bvps, 1) if (cp and bvps and bvps > 0) else None)
    
    phi = sf(info.get("heldPercentInsiders"))
    prom = round(phi * 100, 2) if phi is not None else None
    
    phi_inst = sf(info.get("heldPercentInstitutions"))
    fii = round(phi_inst * 100, 2) if phi_inst is not None else None
    
    pub = round(100 - (prom or 0) - (fii or 0), 2)
    pledged = round(phi * 100, 1) if phi is not None else None

    ebit = sf(info.get("ebit"))
    tot_a = sf(info.get("totalAssets"))
    curr_l = sf(info.get("currentLiabilities") or info.get("totalCurrentLiabilities"))
    roce = round(ebit / (tot_a - curr_l) * 100, 1) if (ebit and tot_a and curr_l and (tot_a - curr_l) != 0) else None

    # Multi-period Returns
    p1d = price_n_days(close, 1)
    p1w = price_n_days(close, 7)
    p1m = price_n_days(close, 30)
    p3m = price_n_days(close, 91)
    p3y = price_n_days(close, 1095)
    p5y = price_n_days(close, 1825)

    yr = close.tail(252) if len(close) >= 252 else close
    low52 = round(float(yr.min()), 2) if not yr.empty else None
    high52 = round(float(yr.max()), 2) if not yr.empty else None
    
    nqlq, yyqq, nq3qb = quarterly_flags(ticker_sym)

    return {
        "Ticker": ticker_sym,
        "Price": cp,
        "MCap (Cr)": mcap_cr,
        "Trend": trend,
        "RS Score": rs_score,
        "F-Score": f_score,
        "Sales Growth % (YoY)": growth.get("Sales Growth % (YoY)"),
        "Profit Growth % (YoY)": growth.get("Profit Growth % (YoY)"),
        "52w Low": low52,
        "52w High": high52,
        "50 DMA": dma50,
        "200 DMA": dma200,
        "RSI": calc_rsi(close),
        "1d Rt %": pct_ret(cp, p1d),
        "1w Rt %": pct_ret(cp, p1w),
        "1m Rt %": pct_ret(cp, p1m),
        "3m Rt %": pct_ret(cp, p3m),
        "1y Rt %": ret1y,
        "3y Rt %": pct_ret(cp, p3y),
        "5y Rt %": pct_ret(cp, p5y),
        "Volatility": rolling_vol(close, 21),
        "Promoter %": prom,
        "FII %": fii,
        "Public %": pub,
        "D/E": de,
        "ROCE %": roce,
        "ROE 1y %": roe1y,
        "ROE 3y %": roe3y,
        "OPM %": opm,
        "Pledged %": pledged,
        "Op Cash 1y (Cr)": op_cf,
        "PE": pe,
        "PBV": pb,
        "Sector": info.get("sector") or "",
        "Industry": info.get("industry") or "",
        "Date": TODAY.date(),
    }
