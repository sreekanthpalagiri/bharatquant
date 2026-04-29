"""
Mathematical and Technical Indicators Module for BharatQuant.

Handles:
1. Technical analysis (RSI, DMA, Volatility).
2. Trend signal detection (Stage 2 Uptrend, Golden Cross).
3. Piotroski F-Score (9-point fundamental health check).
4. Quarterly results tracking.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import timedelta
from .config import TODAY
from .utils import sf, normalise


def price_n_days(close: pd.Series, n: int):
    """
    Return the closing price from approximately N days ago.
    Uses 'normalise' to ensure the date index is clean.
    """
    try:
        c = normalise(close)
        if c.empty:
            return None
        t = pd.Timestamp(TODAY - timedelta(days=n))
        s = c[c.index <= t]
        if s.empty:
            return None
        val = s.iloc[-1]
        return round(float(val.item() if isinstance(val, pd.Series) else val), 4)
    except:
        return None


def calc_rsi(close: pd.Series, period=14):
    """
    Calculate the Relative Strength Index (RSI) for a given period.
    RSI > 70 is overbought, < 30 is oversold.
    """
    try:
        c = normalise(close)
        if c.empty:
            return None
        d = c.diff().dropna()
        g = d.clip(lower=0).ewm(alpha=1 / period, min_periods=period).mean()
        l = (-d).clip(lower=0).ewm(alpha=1 / period, min_periods=period).mean()
        rsi = 100 - (100 / (1 + g / l.replace(0, np.nan)))
        if rsi.empty:
            return None
        val = rsi.iloc[-1]
        return round(float(val.item() if isinstance(val, pd.Series) else val), 1)
    except:
        return None


def rolling_vol(close: pd.Series, n: int):
    """
    Calculate the annualized volatility over the last N days.
    """
    try:
        c = normalise(close)
        if len(c) < n + 1:
            return None
        ret = c.pct_change().dropna().tail(n)
        return round(float(ret.std()) * (252**0.5) * 100, 2)
    except:
        return None


def dma_n(close: pd.Series, n: int):
    """
    Calculate the N-day Simple Moving Average (DMA).
    """
    try:
        c = normalise(close)
        if len(c) < n:
            return None
        ma = c.rolling(window=n).mean()
        if ma.empty:
            return None
        val = ma.iloc[-1]
        return round(float(val.item() if isinstance(val, pd.Series) else val), 2)
    except:
        return None


def get_trend_signal(cp, dma50, dma200) -> str:
    """
    Detect the current technical trend based on 50 and 200 Moving Averages.
    - 'Stage 2': Price > 50 DMA > 200 DMA (Classic Bullish Uptrend).
    - 'Golden Cross': 50 DMA crossed above 200 DMA.
    - 'Death Cross': 50 DMA crossed below 200 DMA.
    """
    if not cp or not dma50 or not dma200:
        return "Unknown"
    
    if cp > dma50 > dma200:
        return "Stage 2 🚀"
    if dma50 > dma200:
        return "Bullish"
    if dma50 < dma200:
        return "Bearish 📉"
    return "Neutral"


def calc_piotroski_score(af: pd.DataFrame, bs: pd.DataFrame, cf: pd.DataFrame) -> int:
    """
    Calculate the 9-point Piotroski F-Score for fundamental health.
    Scale: 0 (Weak) to 9 (Strong). 
    Refactored to be robust against varied yfinance labels and missing data.
    """
    score = 0
    
    # Ensure dataframes have at least 2 years of data for comparisons
    if af.empty or bs.empty or cf.empty or len(af.columns) < 2 or len(bs.columns) < 2:
        return 0

    # Helper to safely extract values
    def get_val(df, keys, year_idx=0):
        # Normalize index for robustness
        idx_map = {str(k).strip().lower(): k for k in df.index}
        for k in keys:
            k_low = k.lower().strip()
            if k_low in idx_map:
                actual_key = idx_map[k_low]
                row = df.loc[actual_key]
                val = sf(row.iloc[year_idx]) if isinstance(row, pd.Series) else sf(row.iloc[0, year_idx])
                if val is not None:
                    return val
        return None

    # 1. Profitability (4 points)
    ni = get_val(af, ["Net Income"])
    ni_prev = get_val(af, ["Net Income"], 1)
    
    ta = get_val(bs, ["Total Assets"])
    ta_prev = get_val(bs, ["Total Assets"], 1)
    
    ocfo = get_val(cf, ["Operating Cash Flow"])
    
    # Point 1: Positive Net Income
    if ni is not None and ni > 0: score += 1
    
    # Point 2: Increasing ROA
    if all(v is not None for v in [ni, ni_prev, ta, ta_prev]):
        roa = ni / ta
        roa_prev = ni_prev / ta_prev
        if roa > roa_prev: score += 1
        
    # Point 3: Positive Operating Cash Flow
    if ocfo is not None and ocfo > 0: score += 1
    
    # Point 4: Quality of Earnings (CFO > NI)
    if ni is not None and ocfo is not None and ocfo > ni: score += 1
    
    # 2. Leverage, Liquidity and Source of Funds (3 points)
    # Point 5: Lower Leverage (Long Term Debt)
    ltd = get_val(bs, ["Long Term Debt", "Long Term Debt And Capital Lease Obligation"])
    ltd_prev = get_val(bs, ["Long Term Debt", "Long Term Debt And Capital Lease Obligation"], 1)
    if ltd is not None and ltd_prev is not None:
        if ltd <= ltd_prev: score += 1
    elif ltd is None: # If no debt, it's good
        score += 1
        
    # Point 6: Improved Liquidity (Current Ratio)
    ca = get_val(bs, ["Current Assets", "Total Current Assets"])
    cl = get_val(bs, ["Current Liabilities", "Total Current Liabilities"])
    ca_prev = get_val(bs, ["Current Assets", "Total Current Assets"], 1)
    cl_prev = get_val(bs, ["Current Liabilities", "Total Current Liabilities"], 1)
    
    if all(v is not None for v in [ca, cl, ca_prev, cl_prev]) and cl != 0 and cl_prev != 0:
        if (ca / cl) > (ca_prev / cl_prev): score += 1
        
    # Point 7: No Equity Dilution
    shares = get_val(bs, ["Ordinary Shares Number", "Ordinary Share Number", "Share Issued"])
    shares_prev = get_val(bs, ["Ordinary Shares Number", "Ordinary Share Number", "Share Issued"], 1)
    if shares is not None and shares_prev is not None:
        if shares <= shares_prev: score += 1
        
    # 3. Operating Efficiency (2 points)
    # Point 8: Improved Gross Margin
    gp = get_val(af, ["Gross Profit"])
    gp_prev = get_val(af, ["Gross Profit"], 1)
    rev = get_val(af, ["Total Revenue", "Operating Revenue"])
    rev_prev = get_val(af, ["Total Revenue", "Operating Revenue"], 1)
    
    if all(v is not None for v in [gp, gp_prev, rev, rev_prev]) and rev != 0 and rev_prev != 0:
        if (gp / rev) > (gp_prev / rev_prev): score += 1
        
    # Point 9: Improved Asset Turnover
    if all(v is not None for v in [rev, rev_prev, ta, ta_prev]) and ta != 0 and ta_prev != 0:
        if (rev / ta) > (rev_prev / ta_prev): score += 1
        
    return score


def quarterly_flags(ticker):
    """
    Placeholder for future quarterly results tracking logic.
    """
    return None, None, None
