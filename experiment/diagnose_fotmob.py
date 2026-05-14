"""
FotMob API diagnostic — run this to check what's happening with the connection.
Usage: python experiment/diagnose_fotmob.py
"""
import requests
import json

BASE_URL = "https://www.fotmob.com/api/"

# Try progressively more browser-like headers
HEADER_SETS = [
    # Minimal
    {"User-Agent": "python-requests/2.31.0"},
    # Browser-like
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-AU,en;q=0.9",
        "Referer": "https://www.fotmob.com/",
        "Origin": "https://www.fotmob.com",
    },
    # With x-mas-locale header (known FotMob requirement in some versions)
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-AU,en;q=0.9",
        "Referer": "https://www.fotmob.com/",
        "x-mas-locale": "en-AU",
    },
]

ENDPOINTS = [
    "allLeagues",
    "leagues?id=47&season=2024%2F2025",  # EPL as a known-good test
]

for endpoint in ENDPOINTS:
    url = BASE_URL + endpoint
    print(f"\n{'='*60}")
    print(f"Endpoint: {url}")
    print(f"{'='*60}")
    for i, headers in enumerate(HEADER_SETS, 1):
        try:
            r = requests.get(url, headers=headers, timeout=10)
            print(f"\n  Header set {i}: status={r.status_code}, "
                  f"content-type={r.headers.get('content-type', 'unknown')}, "
                  f"body_length={len(r.text)}")
            if r.status_code == 200 and r.text.strip():
                try:
                    data = r.json()
                    top_keys = list(data.keys()) if isinstance(data, dict) else f"list[{len(data)}]"
                    print(f"  JSON OK — top-level keys: {top_keys}")
                    # Save first successful response for inspection
                    fname = f"data/fotmob_cache/diag_{endpoint.split('?')[0]}.json"
                    import pathlib
                    pathlib.Path("data/fotmob_cache").mkdir(parents=True, exist_ok=True)
                    with open(fname, "w") as f:
                        json.dump(data, f, indent=2)
                    print(f"  Saved to {fname}")
                    break  # No need to try more headers
                except Exception as e:
                    print(f"  JSON parse failed: {e}")
                    print(f"  Body preview: {r.text[:200]!r}")
            else:
                print(f"  Body preview: {r.text[:200]!r}")
        except Exception as e:
            print(f"  Request failed: {e}")

print("\n\nDone. If all attempts failed, FotMob may require a token/cookie.")
print("Check data/fotmob_cache/ for any saved JSON responses.")
