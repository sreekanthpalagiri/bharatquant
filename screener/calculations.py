import pandas as pd
import numpy as np
import yfinance as yf
from datetime import timedelta
from .config import TODAY
from .utils import sf, normalise


def price_n_days(close: pd.Series, n: int):
    try:
        c = normalise(close)
        if c.empty:
            return None
        t = pd.Timestamp(TODAY - timedelta(days=n))
        s = c[c.index <= t]
        return round(float(s.iloc[-1]), 4) if not s.empty else None
    except:
        return None


def calc_rsi(close: pd.Series, period=14):
    try:
        c = normalise(close)
        if c.empty:
            return None
        d = c.diff().dropna()
        g = d.clip(lower=0).ewm(alpha=1 / period, min_periods=period).mean()
        l = (-d).clip(lower=0).ewm(alpha=1 / period, min_periods=period).mean()
        rsi = 100 - (100 / (1 + g / l.replace(0, np.nan)))
        return round(float(rsi.iloc[-1]), 1) if not rsi.empty else None
    except:
        return None


def rolling_vol(close: pd.Series, n: int):
    try:
        c = normalise(close)
        if len(c) < n + 1:
            return None
        ret = c.pct_change().dropna().tail(n)
        return round(float(ret.std()) * (252**0.5) * 100, 2)
    except:
        return None


def vol_spike_pct(vol: pd.Series, window=20):
    try:
        v = normalise(vol).dropna()
        if len(v) < window + 1:
            return None
        avg = float(v.iloc[-(window + 1) : -1].mean())
        return round((float(v.iloc[-1]) / avg - 1) * 100, 1) if avg else None
    except:
        return None


def prev_vol_pct(vol: pd.Series, window=20):
    try:
        v = normalise(vol).dropna()
        if len(v) < window + 2:
            return None
        avg = float(v.iloc[-(window + 2) : -2].mean())
        return round((float(v.iloc[-2]) / avg - 1) * 100, 1) if avg else None
    except:
        return None


def price_spike_pct(close: pd.Series, window=20):
    try:
        c = normalise(close).dropna()
        if len(c) < window + 1:
            return None
        avg = float(c.iloc[-(window + 1) : -1].mean())
        return round((float(c.iloc[-1]) / avg - 1) * 100, 1) if avg else None
    except:
        return None


def dma_n(close: pd.Series, n=50):
    try:
        c = normalise(close).dropna()
        return round(float(c.tail(n).mean()), 2) if len(c) >= n else None
    except:
        return None


def get_trend_signal(cp, dma50, dma200):
    """Detect Stage 2 uptrend or Golden Cross."""
    if not cp or not dma50 or not dma200:
        return ""
    if cp > dma50 > dma200:
        return "Stage 2"
    if dma50 > dma200:
        return "Golden Cross"
    if dma50 < dma200:
        return "Death Cross"
    return "Neutral"


def calc_piotroski_score(fin: pd.DataFrame, bs: pd.DataFrame, cf: pd.DataFrame):
    """Calculate the 9-point Piotroski F-Score."""
    score = 0
    try:
        if fin.empty or bs.empty or cf.empty:
            return None
        
        # 1. Profitability
        ni = sf(fin.loc["Net Income"].iloc[0])
        tot_a = sf(bs.loc["Total Assets"].iloc[0])
        roa = ni / tot_a if ni and tot_a else 0
        if roa > 0: score += 1 # Positive ROA
        
        cfo = sf(cf.loc["Operating Cash Flow"].iloc[0])
        if cfo and cfo > 0: score += 1 # Positive CFO
        
        ni_prev = sf(fin.loc["Net Income"].iloc[1]) if len(fin.columns) > 1 else None
        tot_a_prev = sf(bs.loc["Total Assets"].iloc[1]) if len(bs.columns) > 1 else None
        roa_prev = ni_prev / tot_a_prev if ni_prev and tot_a_prev else 0
        if roa > roa_prev: score += 1 # Improving ROA
        
        if cfo and ni and cfo > ni: score += 1 # Accrual (CFO > NI)
        
        # 2. Leverage & Liquidity
        # Simplified Leverage (Total Debt / Assets)
        debt = sf(bs.loc["Total Debt"].iloc[0]) if "Total Debt" in bs.index else 0
        lev = debt / tot_a if tot_a else 0
        debt_prev = sf(bs.loc["Total Debt"].iloc[1]) if len(bs.columns) > 1 and "Total Debt" in bs.index else 0
        lev_prev = debt_prev / tot_a_prev if tot_a_prev else 0
        if lev < lev_prev: score += 1 # Decreasing Leverage
        
        # Current Ratio
        ca = sf(bs.loc["Total Current Assets"].iloc[0]) if "Total Current Assets" in bs.index else 0
        cl = sf(bs.loc["Total Current Liabilities"].iloc[0]) if "Total Current Liabilities" in bs.index else 0
        cr = ca / cl if cl else 0
        ca_prev = sf(bs.loc["Total Current Assets"].iloc[1]) if len(bs.columns) > 1 and "Total Current Assets" in bs.index else 0
        cl_prev = sf(bs.loc["Total Current Liabilities"].iloc[1]) if len(bs.columns) > 1 and "Total Current Liabilities" in bs.index else 0
        cr_prev = ca_prev / cl_prev if cl_prev else 0
        if cr > cr_prev: score += 1 # Improving Liquidity
        
        # 3. Efficiency
        rev = sf(fin.loc["Total Revenue"].iloc[0])
        gm = (rev - sf(fin.loc["Cost Of Revenue"].iloc[0])) / rev if rev and "Cost Of Revenue" in fin.index else 0
        rev_prev = sf(fin.loc["Total Revenue"].iloc[1]) if len(fin.columns) > 1 else 0
        gm_prev = (rev_prev - sf(fin.loc["Cost Of Revenue"].iloc[1])) / rev_prev if rev_prev and "Cost Of Revenue" in fin.index else 0
        if gm > gm_prev: score += 1 # Improving Gross Margin
        
        turn = rev / tot_a if tot_a else 0
        turn_prev = rev_prev / tot_a_prev if tot_a_prev else 0
        if turn > turn_prev: score += 1 # Improving Asset Turnover
        
        # No New Shares (Simple check)
        if score < 9: score += 1 # Placeholder for equity issuance check
        
        return score
    except:
        return None


def quarterly_flags(sym: str):
    try:
        qf = yf.Ticker(sym).quarterly_financials
        if qf is None or qf.empty:
            return None, None, None
        ni = None
        for lbl in ["Net Income", "Net Income Common Stockholders"]:
            if lbl in qf.index:
                ni = qf.loc[lbl].sort_index(ascending=False)
                break
        if ni is None:
            return None, None, None
        vals = [sf(v) for v in ni.values[:8]]
        v4 = [v for v in vals[:4] if v is not None]
        v3 = [v for v in vals[:3] if v is not None]
        nqlq = int(all(v > 0 for v in v4)) if len(v4) == 4 else None
        nq3qb = int(all(v > 0 for v in v3)) if len(v3) == 3 else None
        yyqq = (
            int(vals[0] > vals[4]) if (len(vals) >= 5 and vals[0] and vals[4]) else None
        )
        return nqlq, yyqq, nq3qb
    except:
        return None, None, None
