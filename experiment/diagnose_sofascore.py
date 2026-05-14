"""
Quick diagnostic — tests direct page.goto() approach for Sofascore API.
Run: python experiment/diagnose_sofascore.py
"""
import json
import time
from playwright.sync_api import sync_playwright

LEAGUES = {
    'E1':  18,
    'N1':  37,
    'B1':  38,
    'P1':  238,
    'SC0': 36,
    'T1':  52,
    'SWE': 40,
    'NOR': 20,
    'DNK': 39,
    'FIN': 41,
}

def fetch_api(page, url):
    """Navigate directly to API URL and parse JSON from page body."""
    try:
        response = page.goto(url, wait_until='domcontentloaded', timeout=15000)
        if not response or not response.ok:
            status = response.status if response else 0
            return None, status
        content = page.inner_text('body')
        data = json.loads(content)
        return data, response.status
    except Exception as e:
        return None, str(e)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        print("Opening Sofascore to establish session...")
        page.goto('https://www.sofascore.com', wait_until='domcontentloaded')
        time.sleep(3)
        print("Session ready. Testing direct API navigation...\n")

        for code, tid in LEAGUES.items():
            time.sleep(0.5)
            url = f'https://api.sofascore.com/api/v1/unique-tournament/{tid}/seasons'
            data, status = fetch_api(page, url)

            if data and 'seasons' in data:
                seasons = data['seasons']
                latest = seasons[0].get('name', '?') if seasons else 'none'
                print(f"  ✓ {code:4s} (id={tid:3d}) — HTTP {status} — {len(seasons)} seasons, latest: {latest}")
            else:
                print(f"  ✗ {code:4s} (id={tid:3d}) — HTTP {status} — data={str(data)[:80]}")

        browser.close()

if __name__ == '__main__':
    main()
