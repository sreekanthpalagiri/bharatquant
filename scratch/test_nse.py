import requests
from datetime import datetime, timedelta


def test_nse():
    TODAY = datetime.today()
    for days_back in range(10):
        d = TODAY - timedelta(days=days_back)
        dd = d.strftime("%d")
        mmm = d.strftime("%b").upper()
        yyyy = d.strftime("%Y")
        url = (
            f"https://nsearchives.nseindia.com/content/historical/"
            f"EQUITIES/{yyyy}/{mmm}/cm{dd}{mmm}{yyyy}bhav.csv.zip"
        )
        print(f"Testing: {url}")
        try:
            # First hit the home page to get cookies
            s = requests.Session()
            s.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                }
            )
            s.get("https://www.nseindia.com", timeout=10)
            r = s.get(url, timeout=10)
            print(f"  Status: {r.status_code}, Length: {len(r.content)}")
            if r.status_code == 200:
                print("  Success!")
        except Exception as e:
            print(f"  Error: {e}")


if __name__ == "__main__":
    test_nse()
