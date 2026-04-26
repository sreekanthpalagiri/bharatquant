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
        return round(float(s.iloc[-1]), 4) if not s.empty else None
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
        return round(float(rsi.iloc[-1]), 1) if not rsi.empty else None
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
        return round(float(ma.iloc[-1]), 2) if not ma.empty else None
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
    Metrics include Profitability, Leverage, and Operating Efficiency.
    """
    score = 0
    try:
        # Profitability (4 points)
        ni = af.loc["Net Income"].iloc[0]
        ni_prev = af.loc["Net Income"].iloc[1]
        roa = ni / bs.loc["Total Assets"].iloc[0]
        roa_prev = ni_prev / bs.loc["Total Assets"].iloc[1]
        ocfo = cf.loc["Operating Cash Flow"].iloc[0]
        
        if ni > 0: score += 1 # Positive Net Income
        if roa > roa_prev: score += 1 # Increasing ROA
        if ocfo > 0: score += 1 # Positive Operating Cash Flow
        if ocfo > ni: score += 1 # Cash Flow > Net Income (Quality of Earnings)
        
        # Leverage & Liquidity (3 points)
        lt_debt = sf(bs.loc.get("Long Term Debt", pd.Series([0,0])).iloc[0])
        lt_debt_prev = sf(bs.loc.get("Long Term Debt", pd.Series([0,0])).iloc[1])
        if lt_debt <= lt_debt_prev: score += 1 # Lower Leverage
        
        curr_ratio = bs.loc["Total Current Assets"].iloc[0] / bs.loc["Total Current Liabilities"].iloc[0]
        curr_ratio_prev = bs.loc["Total Current Assets"].iloc[1] / bs.loc["Total Current Liabilities"].iloc[1]
        if curr_ratio > curr_ratio_prev: score += 1 # Improved Liquidity
        
        # Shares check
        shares = bs.loc.get("Ordinary Share Number", pd.Series([0,0])).iloc[0]
        shares_prev = bs.loc.get("Ordinary Share Number", pd.Series([0,0])).iloc[1]
        if shares <= shares_prev: score += 1 # No Equity Dilution
        
        # Operating Efficiency (2 points)
        gp = af.loc["Gross Profit"].iloc[0]
        gp_prev = af.loc["Gross Profit"].iloc[1]
        rev = af.loc["Total Revenue"].iloc[0]
        rev_prev = af.loc["Total Revenue"].iloc[1]
        
        if (gp/rev) > (gp_prev/rev_prev): score += 1 # Improved Margin
        if (rev/bs.loc["Total Assets"].iloc[0]) > (rev_prev/bs.loc["Total Assets"].iloc[1]): score += 1 # Higher Asset Turnover
        
    except:
        pass
    return score


def quarterly_flags(ticker):
    """
    Placeholder for future quarterly results tracking logic.
    """
    return None, None, None
