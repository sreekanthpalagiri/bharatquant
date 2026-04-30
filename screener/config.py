import os
import logging
from datetime import datetime

# Path Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)

CONFIG_FILE = os.path.join(CONFIG_DIR, "screener_config.json")

# Default Configuration
DEFAULT_CONFIG = {
    "output": {
        "excel_file": "data/nse_bse_screener.xlsx",
        "ticker_cache_file": "data/tickers_cache.json",
    },
    "schedule": {
        "ticker_cache_days": 14,
        "shares_cache_days": 14,
        "financials_cache_days": 14,
    },
    "filter": {
        "min_mcap_cr": 100,
        "min_price": 5.0,
        "whitelist": [],
        "max_stocks_per_exchange": None,
    },
    "fetch": {"batch_size": 10, "sleep_price_batch": 3.0, "info_workers": 3},
    "logging": {"level": "INFO"},
}


# Helper to load config
def load_config():
    import json

    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return DEFAULT_CONFIG


conf = load_config()

# Global Constants
OUTPUT_FILE = conf["output"]["excel_file"]
TICKER_CACHE_FILE = conf["output"]["ticker_cache_file"]
TICKER_CACHE_DAYS = conf["schedule"].get("ticker_cache_days", 14)
SHARES_CACHE_DAYS = conf["schedule"].get("shares_cache_days", 14)
FINANCIALS_CACHE_DAYS = conf["schedule"].get("financials_cache_days", 14)

MIN_MCAP_CR = conf["filter"]["min_mcap_cr"]
MIN_PRICE = conf["filter"].get("min_price", 5.0)
WHITELIST = [t.upper() for t in conf["filter"].get("whitelist", [])]
MAX_STOCKS_PER_EXCHANGE = conf["filter"]["max_stocks_per_exchange"]
BATCH_SIZE = conf["fetch"]["batch_size"]
SLEEP_PRICE_BATCH = conf["fetch"]["sleep_price_batch"]
INFO_WORKERS = conf["fetch"]["info_workers"]
LOG_LEVEL = conf["logging"]["level"]

# Setup Logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("BharatQuant")

# SILENCE library noise
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("requests").setLevel(logging.CRITICAL)

TODAY = datetime.today()

# Column Definitions
COLUMNS = [
    "Ticker",
    "Name",
    "Trend",
    "RS Score",
    "F-Score",
    "Sales Growth % (YoY)",
    "Profit Growth % (YoY)",
    "Price",
    "MCap (Cr)",
    "P/E",
    "P/B",
    "ROE 1y %",
    "ROE 3y %",
    "ROCE %",
    "D/E",
    "OPM %",
    "Pledged %",
    "RSI",
    "Volatility",
    "50 DMA",
    "200 DMA",
    "1y Rt %",
    "3y Rt %",
    "5y Rt %",
    "Promoter %",
    "FII %",
    "Public %",
    "Sector",
    "Industry",
]

HEADER_LABELS = COLUMNS
WIDTH_MAP = {
    "Ticker": 15,
    "Name": 30,
    "Trend": 15,
    "RS Score": 10,
    "F-Score": 10,
    "Sales Growth % (YoY)": 18,
    "Profit Growth % (YoY)": 18,
    "Price": 12,
    "MCap (Cr)": 12,
    "Sector": 20,
    "Industry": 20,
}
FMT_MAP = {
    "Price": "#,##0.00",
    "MCap (Cr)": "#,##0",
    "P/E": "0.0",
    "P/B": "0.0",
    "F-Score": "0",
    "Sales Growth % (YoY)": "0.0",
    "Profit Growth % (YoY)": "0.0",
    "ROE 1y %": "0.0",
    "ROE 3y %": "0.0",
    "ROCE %": "0.0",
    "D/E": "0.00",
    "OPM %": "0.0",
    "RSI": "0.0",
    "Volatility": "0.0",
    "1y Rt %": "0.0",
    "3y Rt %": "0.0",
    "5y Rt %": "0.0",
    "Promoter %": "0.0",
    "FII %": "0.0",
    "Public %": "0.0",
}

# ------------------------------------------------------------------
# Color Thresholds for Row-Level Formatting (used in exporter)
# ------------------------------------------------------------------
COLOR_RULES = {
    "green": {
        "RS Score": "> 0",
        "F-Score": ">= 7",
        "Growth %": "> 20",
        "ROE 1y %": "> 15",
        "ROE 3y %": "> 15",
        "D/E": "< 1.0",
        "RSI": "30-70",
    },
    "red": {
        "F-Score": "<= 3",
        "Growth %": "< 0",
        "ROE 1y %": "< 5",
        "D/E": ">= 2.0",
    },
    "yellow": {
        "RSI": "<= 30 or >= 70",
    },
}

LEGEND = [
    {"Column": "Ticker / Name", "Description": "Stock identifier and Company Name", "Importance": "Basic identification", "Color Rule": ""},
    {"Column": "Trend", "Description": "Technical stage (e.g., Stage 2, Golden Cross)", "Importance": "Identifies stocks in confirmed bullish uptrends", "Color Rule": "Green if Bullish, Red if Bearish"},
    {"Column": "RS Score", "Description": "Relative Strength vs Nifty 50", "Importance": "Shows outperformance. >0 means it's beating the market.", "Color Rule": "Green if >0, Red if <=0"},
    {"Column": "F-Score", "Description": "Piotroski Health Score (0-9)", "Importance": "7-9 indicates a strong, high-quality turnaround company.", "Color Rule": "Green if >=7, Red if <=4"},
    {"Column": "Sales Growth % (YoY)", "Description": "Revenue growth vs Same Quarter Last Year", "Importance": "Confirms if the business is actually expanding.", "Color Rule": "Green if >20%, Red if <0%"},
    {"Column": "Profit Growth % (YoY)", "Description": "Net Profit growth vs Same Quarter Last Year", "Importance": "Key driver for stock price breakouts.", "Color Rule": "Green if >20%, Red if <0%"},
    {"Column": "Price", "Description": "Current closing price", "Importance": "Latest market valuation.", "Color Rule": ""},
    {"Column": "MCap (Cr)", "Description": "Market Capitalization in ₹ Crores", "Importance": "Filters for company size (e.g., >100 Cr).", "Color Rule": ""},
    {"Column": "P/E / P/B", "Description": "Price-to-Earnings and Price-to-Book", "Importance": "Basic valuation multiples (cheap vs expensive).", "Color Rule": ""},
    {"Column": "ROE (1y / 3y) %", "Description": "Return on Equity (Latest and 3y Average)", "Importance": "Measures how efficiently the company uses shareholder money.", "Color Rule": "Green if >15%, Red if <5%"},
    {"Column": "ROCE %", "Description": "Return on Capital Employed", "Importance": "Measures overall profitability of all capital used.", "Color Rule": ""},
    {"Column": "D/E", "Description": "Debt-to-Equity Ratio", "Importance": "Leverage check. < 1.0 is generally healthy.", "Color Rule": "Green if <1.0, Red if >=2.0"},
    {"Column": "OPM %", "Description": "Operating Profit Margin", "Importance": "Shows the efficiency of the core business operations.", "Color Rule": ""},
    {"Column": "Pledged %", "Description": "% of Promoter shares pledged", "Importance": "Warning sign if high (>25%).", "Color Rule": "Green if <25%, Red if >=50%"},
    {"Column": "RSI", "Description": "Relative Strength Index (14-day)", "Importance": "Shows if the stock is overbought (>70) or oversold (<30).", "Color Rule": "Yellow if between 30 and 70"},
    {"Column": "Volatility", "Description": "1-year annualized price swings", "Importance": "Higher % means more aggressive price movements.", "Color Rule": ""},
    {"Column": "50 / 200 DMA", "Description": "Daily Moving Averages", "Importance": "Used to identify support floors and trend direction.", "Color Rule": ""},
    {"Column": "1y / 3y / 5y Rt %", "Description": "Multi-year Total Returns", "Importance": "Shows historical track record of wealth creation.", "Color Rule": ""},
    {"Column": "Holdings %", "Description": "Promoter, FII, and Public %", "Importance": "Shows 'Smart Money' (FII) interest vs Retail (Public).", "Color Rule": ""},
    {"Column": "Sector / Industry", "Description": "Business categorization", "Importance": "Helps group similar companies for comparison.", "Color Rule": ""},
]
