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
    format="%(asctime)s %(levelname)s %(message)s",
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
