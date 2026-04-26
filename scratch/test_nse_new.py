import requests
from datetime import datetime, timedelta


def test_nse_new():
    TODAY = datetime.today()
    for days_back in range(10):
        d = TODAY - timedelta(days=days_back)
        ds = d.strftime("%d%m%Y")
        url = f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{ds}.csv"
        print(f"Testing: {url}")
        try:
            s = requests.Session()
            s.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                }
            )
            # NSE needs session cookie
            s.get("https://www.nseindia.com", timeout=10)
            r = s.get(url, timeout=10)
            print(f"  Status: {r.status_code}, Length: {len(r.content)}")
            if r.status_code == 200:
                print("  Success!")
                # Print first few lines to see columns
                print(r.text[:200])
                break
        except Exception as e:
            print(f"  Error: {e}")


if __name__ == "__main__":
    test_nse_new()
