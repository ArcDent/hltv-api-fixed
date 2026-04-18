# News HTTP-First Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/api/v1/news` return real news content much more reliably by switching to an HTTP-first multi-strategy fetch flow that only accepts responses that yield parsed article data.

**Architecture:** Introduce a browser-like HTTP-session fetcher and a shared news-content extractor, then refactor the news fetch orchestration to try HTTP first, browser second, and a final fresh HTTP retry last. Fetch success is defined by article extraction, while route status/error contracts stay unchanged.

**Tech Stack:** Python 3.12+, Flask, Scrapy, Selenium, cloudscraper, pytest

---

## File Structure

- Create: `hltv_scraper/news_http_fetcher.py`
- Create: `hltv_scraper/hltv_scraper/news_http_fetcher.py`
- Create: `hltv_scraper/news_content.py`
- Create: `hltv_scraper/hltv_scraper/news_content.py`
- Modify: `hltv_scraper/challenge_fetcher.py`
- Modify: `hltv_scraper/hltv_scraper/challenge_fetcher.py`
- Modify: `hltv_scraper/hltv_scraper/spiders/parsers/news.py`
- Modify: `tests/test_browser_fetcher.py`
- Modify: `tests/test_news_parser.py`
- Modify: `tests/test_news_pipeline.py`

### Task 1: Add failing HTTP-first orchestration regressions

**Files:**
- Modify: `tests/test_browser_fetcher.py`
- Modify: `tests/test_news_parser.py`

- [ ] **Step 1: Add a red test proving parseable HTTP content should short-circuit before browser**

Add a test to `tests/test_browser_fetcher.py` that patches the future HTTP-session fetch helper to return a parseable `HtmlResponse`, patches `BrowserHTMLFetcher.fetch` to raise if called, and asserts `fetch_hltv_page(...)` returns the HTTP response text without touching browser code.

- [ ] **Step 2: Run the single new orchestration test and verify it fails**

Run: `./env/bin/python -m pytest tests/test_browser_fetcher.py -k http_first_short_circuits_browser -v`

Expected: FAIL because the current implementation is browser-first and has no HTTP-session fetch helper to satisfy the behavior.

- [ ] **Step 3: Add a red test proving hard-blocked HTTP content falls through to browser and succeeds there**

Add a test to `tests/test_browser_fetcher.py` that patches the future HTTP-session fetch helper to raise `NewsScrapeFetchError(reason="challenge_detected")`, patches browser fetch to return parseable article HTML, and asserts `fetch_hltv_page(...)` returns the browser response.

- [ ] **Step 4: Run the browser-fallback orchestration test and verify it fails**

Run: `./env/bin/python -m pytest tests/test_browser_fetcher.py -k blocked_http_falls_back_to_browser -v`

Expected: FAIL because the current code never attempts HTTP first and therefore cannot express this fallback ordering.

- [ ] **Step 5: Add a red parser/extractor reuse test**

Add a test to `tests/test_news_parser.py` asserting that parseable JSON-LD-only archive HTML still produces one article via the shared extraction path after the parser refactor.

- [ ] **Step 6: Run the new parser-focused test and verify it fails for the expected missing shared helper path**

Run: `./env/bin/python -m pytest tests/test_news_parser.py -k shared_extractor -v`

Expected: FAIL because the shared extractor module does not exist yet.

### Task 2: Implement shared content extraction and HTTP-session fetcher

**Files:**
- Create: `hltv_scraper/news_content.py`
- Create: `hltv_scraper/hltv_scraper/news_content.py`
- Create: `hltv_scraper/news_http_fetcher.py`
- Create: `hltv_scraper/hltv_scraper/news_http_fetcher.py`
- Modify: `hltv_scraper/hltv_scraper/spiders/parsers/news.py`

- [ ] **Step 1: Create the shared extractor module in both package roots**

Implement matching `news_content.py` modules that expose:

- `extract_news_articles(response) -> list[dict]`
- `_parse_css_articles(response)`
- `_parse_jsonld_articles(response)`
- `_walk_json(data)`
- `_is_news_article(item)`
- `_clean(value)`

Use the exact article dict shape already returned by `NewsParser`.

- [ ] **Step 2: Run the parser-focused test and verify it still fails until `NewsParser` is switched over**

Run: `./env/bin/python -m pytest tests/test_news_parser.py -k shared_extractor -v`

Expected: FAIL if the parser still uses its old private implementation.

- [ ] **Step 3: Refactor `NewsParser` to delegate to the shared extractor**

Update `hltv_scraper/hltv_scraper/spiders/parsers/news.py` so `parse()` does:

1. blocked-page check,
2. `articles = extract_news_articles(response)`,
3. return `articles` if non-empty,
4. otherwise raise `NewsScrapeContentError`.

- [ ] **Step 4: Create the browser-like HTTP-session fetcher in both package roots**

Implement matching `news_http_fetcher.py` modules with a function like `fetch_news_archive_with_http_session(url: str) -> HtmlResponse` that:

- creates a fresh `cloudscraper` session,
- sets browser-like headers,
- warms up `https://www.hltv.org/`,
- requests the archive URL,
- returns `build_html_response(response.url, response.text)`,
- raises `NewsScrapeFetchError(..., reason="fallback_failed")` on request exceptions.

- [ ] **Step 5: Run the parser suite and verify the parser-focused red test turns green**

Run: `./env/bin/python -m pytest tests/test_news_parser.py -v`

Expected: PASS for the parser suite, while the HTTP-first orchestration tests remain red.

### Task 3: Refactor news fetch orchestration to HTTP-first with parseability-based success

**Files:**
- Modify: `hltv_scraper/challenge_fetcher.py`
- Modify: `hltv_scraper/hltv_scraper/challenge_fetcher.py`
- Test: `tests/test_browser_fetcher.py`
- Test: `tests/test_news_pipeline.py`

- [ ] **Step 1: Update both `challenge_fetcher.py` files to orchestrate strategies in this order**

Implement this behavior:

1. try HTTP session,
2. if the candidate is blocked or yields zero extracted articles, record the error and continue,
3. try browser fetch,
4. if browser candidate is blocked or yields zero extracted articles, record the error and continue,
5. try one final fresh HTTP session retry,
6. raise the last meaningful `NewsScrapeFetchError`.

Use `extract_news_articles(response)` as the success check.

- [ ] **Step 2: Keep blocked-page detection for truly challenge-only HTML**

Continue using `is_blocked_archive_page(response.text)` so obviously blocked pages still return `challenge_detected`.

- [ ] **Step 3: Run the two orchestration red tests and verify they now pass**

Run: `./env/bin/python -m pytest tests/test_browser_fetcher.py -k "http_first_short_circuits_browser or blocked_http_falls_back_to_browser" -v`

Expected: PASS.

- [ ] **Step 4: Run the full browser-fetcher suite to catch regressions across outer and Scrapy-cwd paths**

Run: `./env/bin/python -m pytest tests/test_browser_fetcher.py -v`

Expected: PASS.

- [ ] **Step 5: Run the news pipeline suite to ensure strict fetch-reason propagation still holds**

Run: `./env/bin/python -m pytest tests/test_news_pipeline.py -v`

Expected: PASS.

### Task 4: Final verification and live spot-check

**Files:**
- Test: `tests/test_browser_fetcher.py`
- Test: `tests/test_news_parser.py`
- Test: `tests/test_news_pipeline.py`
- Test: `tests/test_routes.py`

- [ ] **Step 1: Run all news-related suites together**

Run: `./env/bin/python -m pytest tests/test_browser_fetcher.py tests/test_news_parser.py tests/test_news_pipeline.py tests/test_routes.py -v`

Expected: PASS with zero failures.

- [ ] **Step 2: Start the worktree server and hit the news archive endpoint once**

Run: `./env/bin/python -c "from app import create_app; app = create_app(); app.run(host='127.0.0.1', port=8010)" >/dev/null 2>&1 & pid=$!; sleep 5; curl -sS -i http://127.0.0.1:8010/api/v1/news/2026/April/; status=$?; kill $pid; wait $pid || true; exit $status`

Expected: either a `200` with a news list or, if HLTV is actively blocking at that moment, a `502` whose `reason` reflects the last meaningful fetch failure rather than a silent contract collapse.

- [ ] **Step 3: Report exact outcomes and the remaining live-risk honestly**

Summarize:

- test command output,
- live endpoint response,
- whether stability improved,
- and any remaining external-risk caveat from HLTV/Cloudflare variability.
