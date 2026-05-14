/no_think

Fix a single function in an existing Python script. Do not change anything else.

## File to edit
`experiment/load_sofascore.py`

## The problem
`fetch_json()` uses `page.evaluate()` to run a JavaScript `fetch()` call inside the browser. This fails with "TypeError: Failed to fetch" because Sofascore's Content Security Policy blocks JavaScript-initiated cross-origin requests to `api.sofascore.com`.

## The fix
Replace `fetch_json()` with a version that uses `page.goto()` to navigate directly to the API URL, then reads the JSON from the page body. Direct navigation is not subject to CSP.

This approach is confirmed working — a diagnostic script tested all 10 leagues with `page.goto()` and got HTTP 200 + valid JSON from every one.

## Exact replacement

Remove this function:

```python
def fetch_json(page, url):
    """Make a fetch() call inside the browser. Returns parsed JSON or None."""
    # IMPORTANT: use page.evaluate() not requests.get() — auth is handled by browser
    result = page.evaluate(f"""
        async () => {{
            try {{
                const r = await fetch('{url}', {{headers: {{'Accept': 'application/json'}}, credentials: 'include'}});
                if (!r.ok) return null;
                return await r.json();
            }} catch(e) {{
                return null;
            }}
        }}
    """)
    return result
```

Replace it with this:

```python
def fetch_json(page, url):
    """Navigate directly to API URL and parse JSON from page body. Returns parsed JSON or None."""
    try:
        response = page.goto(url, wait_until='domcontentloaded', timeout=15000)
        if not response or not response.ok:
            return None
        content = page.inner_text('body')
        return json.loads(content)
    except Exception:
        return None
```

Also add `import json` to the imports at the top of the file (after `import time`).

## What NOT to change
- Do not change any other function
- Do not change LEAGUES, STAT_MAP, OUTPUT_COLUMNS, MAX_ROUNDS, DELAY, or any constants
- Do not change get_seasons(), get_round_matches(), get_match_stats(), scrape_season(), or main()
- The sofascore.com session establishment step in main() can stay — it's harmless

## Output
Return only the complete updated `experiment/load_sofascore.py`. No explanation needed.
