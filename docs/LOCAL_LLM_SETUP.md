# Local LLM Setup

*Updated 2026-04-29. Benchmarked on Chris's hardware.*
**Workflow:** use the `local-llm` Cowork skill. This file covers hardware specs and benchmarks only.

## Hardware

| Component | Spec |
|---|---|
| GPU | NVIDIA RTX 5070, 8GB GDDR7 |
| CPU | Intel Core Ultra 9 275HX, 24 cores |
| RAM | 32GB DDR5 5600 MT/s |
| OS | Windows 11 |

## Installed Models

Always use the `-16k` context variants.

| Model | Tag | Type | VRAM | Speed | Use For |
|---|---|---|---|---|---|
| Qwen3-Coder 30B | `qwen3-coder:30b-16k` | MoE (3B active) | 8GB + ~10GB RAM | 22.7 tok/s | Default. Pipeline scripts, data transforms, boilerplate |
| Gemma 4 26B | `gemma4:26b-16k` | MoE (4B active) | 8GB + ~10GB RAM | 17.0 tok/s | Correctness-critical. Async code, financial calcs |
| Qwen3 8B | `qwen3:8b-16k` | Dense | ~5.2GB | 35-40 tok/s | Quick edits. Config, single functions, test stubs |

Note: `qwen3-coder:8b` does not exist in Ollama. Use `qwen3:8b` for the 8B class.

## Prompt Settings

Include in every local model prompt:
```
temperature: 0.2
num_predict: 4096
```
Prefix all Qwen3 model prompts with `/no_think` to suppress verbose reasoning output.

## Running a Model

```powershell
ollama run qwen3-coder:30b-16k
```

Then paste your prompt. Local models have no project context — they see only what you paste. For multi-file work, use Sonnet CLI instead.

## Benchmark Comparison

Task: write `telegram_sender.py` with MarkdownV2 formatting, error handling, and rate limiting.

| | Qwen3-Coder 30B | Gemma 4 26B |
|---|---|---|
| Speed | 22.7 tok/s | 17.0 tok/s |
| Wall time | 57s | 180s |
| Output size | 820 tokens | 2679 tokens |
| Quality checks passed | 7/8 | 8/8 |
| Async API | No | Yes |
| MarkdownV2 escape handling | Missing | Correct |
| Output complete | Yes | Yes (needs 4096 cap) |

## Known Limitations

- **Qwen3-Coder 30B:** misses edge cases (e.g. MarkdownV2 escaping, async patterns). Review output for subtle bugs. Fast enough to iterate.
- **Gemma 4 26B:** verbose — truncates at `num_predict: 2048`. Always use 4096. Worth the extra time for correctness-critical modules.
- **No agentic capability:** local models generate code, they don't run it, test it, or iterate. You run the output manually.

## Data Source Notes (Session 9)

**FBref is not scrapeable.** Cloudflare bot detection blocks all automated approaches:
plain requests (403), cloudscraper (403), Playwright headless (challenge page),
Playwright visible (CAPTCHA loop — detects `navigator.webdriver`). Do not attempt
FBref scraping in future prompts. Use FotMob for match stats instead.

**FotMob** (unofficial API, no auth) is the confirmed stats source for all leagues.
Provides shots, SoT, corners, fouls, cards, and xG. Community Python packages exist
(`fotmob` on PyPI). One-time historical scrape, cache to disk.

---

## Qwen3-Coder Bug Patterns (observed Session 9, Modules 1–2)

These bugs appeared in multiple outputs. Future prompts should explicitly guard against them.

### 1. Deprecated pandas API — `pd.compat.StringIO`
Qwen uses `pd.read_csv(pd.compat.StringIO(...))` which was removed in pandas 1.0.
**Fix in prompt:** Always specify `import io` and `pd.read_csv(io.StringIO(...))` explicitly.

### 2. Column rename omitted — silent all-NaN output
Qwen builds the correct output schema with `reindex(columns=OUTPUT_SCHEMA)` but forgets to
rename the source columns first. The file saves without error but every data column is NaN.
**Fix in prompt:** Show the explicit rename map and say "rename columns BEFORE reindex". Example:
```python
RENAME = {'RawCol': 'output_col', ...}
df = df.rename(columns=RENAME).reindex(columns=OUTPUT_SCHEMA)
```

### 3. Mixed format categories applied to wrong items
When there are two variants of something (e.g. European vs calendar-year seasons, or
standard vs new-format CSV columns), Qwen tends to apply both variants to all items
rather than routing each item to its correct variant.
**Fix in prompt:** Explicitly state "league X uses format A, league Y uses format B — do not
mix them". Provide a per-item lookup table rather than a generic rule.

### 4. Module-level side effects (cache init, global state)
Qwen initialises `requests_cache`, opens files, or sets global state at module level
(outside `main()`). This breaks `--no-cache` flags and causes crashes when directories
don't exist yet.
**Fix in prompt:** State explicitly "all initialisation happens inside `main()` after argument
parsing. Nothing that touches the filesystem runs at import time."

### 5. Date format not converted
Qwen notes "output as YYYY-MM-DD" in a docstring but returns the raw source string without
actually parsing it. Looks correct in code review but fails at runtime or produces
wrong-format dates silently.
**Fix in prompt:** Provide the exact `strftime` conversion: `pd.to_datetime(series,
dayfirst=True).dt.strftime('%Y-%m-%d')` or equivalent. Don't just describe the format.

### 6. Overly broad HTML selectors
When scraping HTML, Qwen uses selectors that are too broad (e.g. `find_all('strong')` on
an entire page or section) and accidentally captures elements from adjacent content.
**Fix in prompt:** Specify the exact parent container to search within, and the exact
`data-stat` attribute or CSS class to target. Example: "find `<td data-stat='home_team'>`
inside the `<tr>` — do not search the whole page".
