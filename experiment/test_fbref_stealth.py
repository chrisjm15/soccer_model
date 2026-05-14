"""
FBref stealth test — checks whether playwright-stealth bypasses bot detection.
A real Chrome window will open. Watch it — if a CAPTCHA appears, solve it manually.

Usage:
    pip install playwright-stealth
    python experiment/test_fbref_stealth.py
"""

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import time

TEST_URL = "https://fbref.com/en/comps/10/stats/Championship-Stats"

def main():
    print("Launching visible Chrome with stealth patches...")
    print("Watch the browser window. If a CAPTCHA appears, solve it manually.\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",  # use real installed Chrome, not bundled Chromium
            args=["--start-maximized"],
        )
        context = browser.new_context(
            viewport=None,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        # Apply stealth patches — masks navigator.webdriver and other fingerprints
        Stealth().apply_stealth_sync(page)

        print(f"Navigating to: {TEST_URL}")
        try:
            page.goto(TEST_URL, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"Navigation error: {e}")
            browser.close()
            return

        # --- Handle Cloudflare challenge ---
        # Wait up to 60 seconds for either the challenge to auto-pass
        # or for you to solve it manually
        print("\nChecking for Cloudflare challenge...")
        deadline = time.time() + 60
        while time.time() < deadline:
            title = page.title()
            if "just a moment" in title.lower() or "checking" in title.lower():
                print(f"  Cloudflare challenge active (title: '{title}') — solve it in the browser window...")
                time.sleep(3)
            else:
                print(f"  Challenge cleared. Title: '{title}'")
                break
        else:
            print("  Timed out waiting for challenge to clear.")
            browser.close()
            return

        # --- Wait for actual FBref page content to load ---
        print("\nWaiting for FBref page content...")
        try:
            # Wait for a stats table to appear — this confirms real content loaded
            page.wait_for_selector("table", timeout=20000)
        except Exception:
            print("  No table found within 20 seconds.")

        # Final check
        title = page.title()
        url = page.url
        body_text = page.inner_text("body")[:2000]

        print(f"\nFinal URL:   {url}")
        print(f"Page title:  {title}")

        if "403" in title or "access denied" in body_text.lower():
            print("\nRESULT: Hard block — access denied.")

        elif "Championship" in title or "FBref" in body_text or "fbref" in url:
            print("\nRESULT: SUCCESS — FBref page loaded after CAPTCHA solve.")

            # Check for xG data specifically
            if "xG" in body_text:
                print("xG columns CONFIRMED present in page content.")
            else:
                print("xG not found in first 2000 chars — checking further down...")
                full_text = page.inner_text("body")
                if "xG" in full_text:
                    print("xG columns CONFIRMED present (deeper in page).")
                else:
                    print("WARNING: xG not found anywhere on page — may not be available for this league/season.")
        else:
            print(f"\nRESULT: Unclear.")
            print(f"Body preview:\n{body_text[:500]}")

        print("\nBrowser will stay open for 15 seconds so you can inspect it...")
        time.sleep(15)
        browser.close()

if __name__ == "__main__":
    main()
