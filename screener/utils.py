import pandas as pd
import requests


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-IN,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
    )
    return s


SESSION = make_session()


def clean_code(raw) -> str:
    """
    Sanitise a BSE scrip code or NSE symbol.
    """
    s = str(raw).strip().lstrip("$£€₹ \t")
    if s.endswith(".0"):
        s = s[:-2]
    return s


def sf(val, d=2):
    try:
        if val is None:
            return None
        f = float(val)
        return None if (f != f or abs(f) == float("inf")) else round(f, d)
    except:
        return None


def pct_ret(new, old):
    if new and old and old != 0:
        return round((new - old) / old * 100, 2)
    return None


def normalise(series: pd.Series) -> pd.Series:
    """
    Ensure a Series has a tz-naive DatetimeIndex.
    """
    if series is None or series.empty:
        return pd.Series(dtype=float)
    try:
        if not isinstance(series.index, pd.DatetimeIndex):
            series = series.copy()
            series.index = pd.to_datetime(series.index)
        if series.index.tz is not None:
            series = series.copy()
            series.index = series.index.tz_localize(None)
    except Exception:
        return pd.Series(dtype=float)
    return series
