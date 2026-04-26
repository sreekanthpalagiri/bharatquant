import yfinance as yf
import json


def inspect_ticker(sym):
    print(f"Inspecting: {sym}")
    t = yf.Ticker(sym)

    print("\n--- .info keys ---")
    info = t.info
    if info:
        keys = sorted(list(info.keys()))
        print(f"Total keys: {len(keys)}")
        for k in keys:
            if "share" in k.lower() or "cap" in k.lower() or "price" in k.lower():
                print(f"  {k}: {info.get(k)}")
    else:
        print("  .info is empty or failed")

    print("\n--- .fast_info ---")
    try:
        fi = t.fast_info
        for attr in dir(fi):
            if not attr.startswith("_"):
                try:
                    val = getattr(fi, attr)
                    if not callable(val):
                        if (
                            "share" in attr.lower()
                            or "cap" in attr.lower()
                            or "price" in attr.lower()
                        ):
                            print(f"  {attr}: {val}")
                except:
                    pass
    except Exception as e:
        print(f"  .fast_info failed: {e}")


if __name__ == "__main__":
    inspect_ticker("RELIANCE.NS")
    inspect_ticker("500325.BO")
