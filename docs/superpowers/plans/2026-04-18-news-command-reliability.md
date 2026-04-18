# News Command Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/api/v1/news` stop misclassifying valid HLTV archive pages as Cloudflare challenge pages and preserve fetch-error reasons instead of occasionally collapsing into `missing_output`.

**Architecture:** Introduce one shared HTML-classification helper for HLTV news archive pages, then make both the fetcher and parser trust that shared classification so pages with real articles are accepted even if Cloudflare scripts are also present. Harden strict-mode fetch error propagation by emitting the `HLTV_NEWS_FETCH_REASON` marker directly from the spider before re-raising, then verify with targeted tests and the unit suite.

**Tech Stack:** Python 3.12, Flask, Scrapy, Selenium, cloudscraper, pytest

**Execution note:** Do not create git commits during execution unless the user explicitly requests them.

---

## File Structure

- Create: `hltv_scraper/news_page_detection.py` — pure helper functions for identifying archive-content markers vs challenge markers.
- Modify: `hltv_scraper/challenge_fetcher.py` — use shared page classification and only reject pages that are blocked *and* lack archive content.
- Modify: `hltv_scraper/hltv_scraper/spiders/parsers/news.py` — use the same classifier so parser-side challenge handling matches fetcher behavior.
- Modify: `hltv_scraper/hltv_scraper/spiders/hltv_news.py` — print the fetch marker before re-raising so strict subprocess parsing remains stable.
- Modify: `tests/test_browser_fetcher.py` — add mixed-content regression tests for browser/fallback HTML.
- Modify: `tests/test_news_parser.py` — add parser regression for pages containing both article data and Cloudflare markers.
- Modify: `tests/test_news_pipeline.py` — add strict-process regression for marker extraction from plain log output.

### Task 1: Bootstrap repo-local test environment and add failing regressions

**Files:**
- Modify: `tests/test_browser_fetcher.py`
- Modify: `tests/test_news_parser.py`
- Modify: `tests/test_news_pipeline.py`

- [ ] **Step 1: Create the repo-local virtualenv expected by this repository**

Run:

```bash
python3 -m venv env
./env/bin/pip install -r requirements.txt
```

Expected: virtualenv created at `./env`, pip finishes successfully, pytest becomes available at `./env/bin/python -m pytest`.

- [ ] **Step 2: Write a failing fetcher regression for browser HTML that contains both articles and Cloudflare script markers**

Add this test to `tests/test_browser_fetcher.py`:

```python
def test_fetch_hltv_page_accepts_browser_html_when_articles_exist_alongside_cloudflare_markers():
    from hltv_scraper.challenge_fetcher import fetch_hltv_page
    from hltv_scraper.browser_fetcher import BrowserFetchResult

    browser_result = BrowserFetchResult(
        final_url="https://www.hltv.org/news/archive/2026/april",
        html="""
        <html>
          <head>
            <link rel="canonical" href="https://www.hltv.org/news/archive/2026/april" />
            <script type="application/ld+json">
              {
                "@context": "https://schema.org",
                "@type": "NewsArticle",
                "headline": "Major event announced",
                "url": "https://www.hltv.org/news/1/major-event-announced"
              }
            </script>
            <script>window.__CF$cv$params = {};</script>
          </head>
          <body>
            <a class="newsline article" href="/news/1/major-event-announced">
              <div class="newstext">Major event announced</div>
            </a>
          </body>
        </html>
        """,
    )

    with patch(
        "hltv_scraper.challenge_fetcher.BrowserHTMLFetcher.fetch",
        return_value=browser_result,
    ):
        response = fetch_hltv_page("https://www.hltv.org/news/archive/2026/April")

    assert response.url == "https://www.hltv.org/news/archive/2026/april"
    assert "Major event announced" in response.text
```

- [ ] **Step 3: Run the new fetcher regression to verify the current code fails**

Run:

```bash
./env/bin/python -m pytest tests/test_browser_fetcher.py::test_fetch_hltv_page_accepts_browser_html_when_articles_exist_alongside_cloudflare_markers -v
```

Expected: FAIL with `NewsScrapeFetchError` because `challenge_fetcher.py` currently rejects any page containing Cloudflare markers before checking whether article content is already present.

- [ ] **Step 4: Write a failing parser regression for mixed archive/challenge HTML**

Add this test to `tests/test_news_parser.py`:

```python
def test_news_parser_accepts_articles_when_cloudflare_markers_coexist_with_archive_content():
    response = _response_from_html(
        """
        <html>
          <head>
            <script type="application/ld+json">
              {
                "@context": "https://schema.org",
                "@type": "NewsArticle",
                "headline": "Mixed page title",
                "url": "https://www.hltv.org/news/500/mixed-page-title"
              }
            </script>
            <script>window.__CF$cv$params = {};</script>
          </head>
          <body>
            <a class="newsline article" href="/news/500/mixed-page-title">
              <div class="newstext">Mixed page title</div>
            </a>
          </body>
        </html>
        """
    )

    assert NewsParser.parse(response) == [
        {
            "title": "Mixed page title",
            "img": None,
            "date": None,
            "comments": None,
            "link": "https://www.hltv.org/news/500/mixed-page-title",
        }
    ]
```

- [ ] **Step 5: Run the parser regression to verify the current code fails**

Run:

```bash
./env/bin/python -m pytest tests/test_news_parser.py::test_news_parser_accepts_articles_when_cloudflare_markers_coexist_with_archive_content -v
```

Expected: FAIL with `NewsScrapeContentError` because parser challenge detection runs before article parsing and treats any challenge marker as fatal.

- [ ] **Step 6: Write a failing strict-process regression for plain marker log output**

Add this test to `tests/test_news_pipeline.py`:

```python
def test_spider_process_execute_strict_raises_fetch_error_from_plain_marker_line():
    from hltv_scraper.errors import NewsScrapeFetchError

    process = Mock()
    process.communicate.return_value = (
        "HLTV_NEWS_FETCH_REASON:challenge_detected:Browser fetch reached a challenge page instead of the news archive page.\n",
        "",
    )
    process.returncode = 0

    with patch("hltv_scraper.process.subprocess.Popen", return_value=process):
        with pytest.raises(NewsScrapeFetchError) as exc_info:
            SpiderProcess().execute(
                "hltv_news",
                "/tmp",
                "-a year=2026 -a month=April -o data/news/news_2026_April.json",
                strict=True,
            )

    assert exc_info.value.reason == "challenge_detected"
    assert (
        str(exc_info.value)
        == "Browser fetch reached a challenge page instead of the news archive page."
    )
```

- [ ] **Step 7: Run the new strict-process regression to verify the red case**

Run:

```bash
./env/bin/python -m pytest tests/test_news_pipeline.py::test_spider_process_execute_strict_raises_fetch_error_from_plain_marker_line -v
```

Expected: PASS immediately. This is acceptable because the process extractor already supports plain marker lines; the test locks in the behavior needed for the spider-side hardening in Task 3.

### Task 2: Implement shared archive-page classification and update fetcher/parser behavior

**Files:**
- Create: `hltv_scraper/news_page_detection.py`
- Modify: `hltv_scraper/challenge_fetcher.py`
- Modify: `hltv_scraper/hltv_scraper/spiders/parsers/news.py`
- Test: `tests/test_browser_fetcher.py`
- Test: `tests/test_news_parser.py`

- [ ] **Step 1: Create a shared page-classification helper module**

Create `hltv_scraper/news_page_detection.py` with this code:

```python
CHALLENGE_MARKERS = (
    "just a moment...",
    "checking your browser before accessing",
    "cf-browser-verification",
    "attention required! | cloudflare",
    "window.__cf$cv$params",
    "/cdn-cgi/challenge-platform/",
)


def has_archive_content(html: str) -> bool:
    normalized = (html or "").lower()
    has_news_jsonld = (
        "application/ld+json" in normalized
        and '"@type"' in normalized
        and "newsarticle" in normalized
    )
    return (
        "a.newsline.article" in normalized
        or "newsline article" in normalized
        or has_news_jsonld
    )


def has_challenge_markers(html: str) -> bool:
    normalized = (html or "").lower()
    return any(marker in normalized for marker in CHALLENGE_MARKERS)


def is_blocked_archive_page(html: str) -> bool:
    return has_challenge_markers(html) and not has_archive_content(html)
```

- [ ] **Step 2: Replace the fetcher’s inline challenge/archive detection with the shared helper**

Update `hltv_scraper/challenge_fetcher.py` so its decision flow becomes:

```python
import cloudscraper
from scrapy.http import HtmlResponse

from .browser_fetcher import BrowserHTMLFetcher
from .errors import NewsScrapeFetchError
from .news_page_detection import has_archive_content, is_blocked_archive_page
from .response_factory import build_html_response


def fetch_hltv_page(url: str) -> HtmlResponse:
    try:
        browser_result = BrowserHTMLFetcher().fetch(url)
        if is_blocked_archive_page(browser_result.html):
            raise NewsScrapeFetchError(
                "Browser fetch reached a challenge page instead of the news archive page.",
                reason="challenge_detected",
            )
        if not has_archive_content(browser_result.html):
            raise NewsScrapeFetchError(
                "Browser fetch did not return expected news archive content.",
                reason="challenge_detected",
            )
        return build_html_response(browser_result.final_url, browser_result.html)
    except NewsScrapeFetchError as browser_error:
        if browser_error.reason not in {"browser_timeout", "browser_fetch_failed"}:
            raise

        scraper = cloudscraper.create_scraper()
        try:
            fallback_response = scraper.get(url, timeout=20)
        except Exception as exc:
            raise NewsScrapeFetchError(
                "Fallback fetch failed for the news archive page.",
                reason="fallback_failed",
            ) from exc

        if is_blocked_archive_page(fallback_response.text):
            raise NewsScrapeFetchError(
                "News archive fetch is still blocked by a challenge page.",
                reason="challenge_detected",
            )

        if not has_archive_content(fallback_response.text):
            raise NewsScrapeFetchError(
                "Fallback fetch did not return expected news archive content.",
                reason="challenge_detected",
            )

        return build_html_response(fallback_response.url, fallback_response.text)
```

- [ ] **Step 3: Update parser-side challenge handling to use the same content-aware logic**

Update `hltv_scraper/hltv_scraper/spiders/parsers/news.py` like this:

```python
import json
from typing import Any

from hltv_scraper.errors import NewsScrapeContentError
from hltv_scraper.news_page_detection import has_archive_content, is_blocked_archive_page
from .parser import Parser


class NewsParser(Parser):
    @staticmethod
    def _raise_if_challenge_page(response) -> None:
        html = response.text or ""
        if has_archive_content(html):
            return
        if is_blocked_archive_page(html):
            raise NewsScrapeContentError(
                "News archive page is a challenge page and cannot be parsed."
            )
```

- [ ] **Step 4: Run the mixed-content fetcher and parser regressions**

Run:

```bash
./env/bin/python -m pytest \
  tests/test_browser_fetcher.py::test_fetch_hltv_page_accepts_browser_html_when_articles_exist_alongside_cloudflare_markers \
  tests/test_news_parser.py::test_news_parser_accepts_articles_when_cloudflare_markers_coexist_with_archive_content \
  -v
```

Expected: PASS for both tests.

- [ ] **Step 5: Run the full news fetcher/parser test files to catch regressions**

Run:

```bash
./env/bin/python -m pytest tests/test_browser_fetcher.py tests/test_news_parser.py -v
```

Expected: all tests in both files PASS.

### Task 3: Harden fetch-reason propagation and verify the route-level contract

**Files:**
- Modify: `hltv_scraper/hltv_scraper/spiders/hltv_news.py`
- Modify: `tests/test_news_pipeline.py`
- Modify: `tests/test_routes.py` (only if the existing route suite needs an explicit contract lock; otherwise no code change required)

- [ ] **Step 1: Emit the fetch marker directly from the spider before re-raising**

Update `hltv_scraper/hltv_scraper/spiders/hltv_news.py`:

```python
import sys
import scrapy
from typing import Any, Generator

from hltv_scraper.challenge_fetcher import fetch_hltv_page
from hltv_scraper.errors import NewsScrapeFetchError

from .parsers import ParsersFactory as PF


class HltvNewsSpider(scrapy.Spider):
    ...

    def start_requests(self) -> Generator[Any, Any, None]:
        try:
            response = fetch_hltv_page(self.archive_url)
        except NewsScrapeFetchError as exc:
            marker = f"HLTV_NEWS_FETCH_REASON:{exc.reason}:{str(exc)}"
            print(marker, file=sys.stderr)
            raise RuntimeError(marker) from exc
        yield from self.parse(response)
```

- [ ] **Step 2: Add or update a spider regression that locks in the marker string**

If you need an explicit spider-level test, extend `tests/test_news_pipeline.py` with:

```python
def test_hltv_news_spider_start_requests_prints_fetch_marker_before_raising(monkeypatch):
    from hltv_scraper.errors import NewsScrapeFetchError
    from hltv_scraper.hltv_scraper.spiders.hltv_news import HltvNewsSpider

    printed: list[str] = []

    def fake_print(message, file=None):
        printed.append(message)

    spider = HltvNewsSpider(year="2026", month="April")

    monkeypatch.setattr("builtins.print", fake_print)

    with patch(
        "hltv_scraper.hltv_scraper.spiders.hltv_news.fetch_hltv_page",
        side_effect=NewsScrapeFetchError(
            "Browser fetch reached a challenge page instead of the news archive page.",
            reason="challenge_detected",
        ),
    ):
        with pytest.raises(RuntimeError):
            list(spider.start_requests())

    assert printed == [
        "HLTV_NEWS_FETCH_REASON:challenge_detected:Browser fetch reached a challenge page instead of the news archive page."
    ]
```

- [ ] **Step 3: Run the pipeline regressions for marker extraction and spider propagation**

Run:

```bash
./env/bin/python -m pytest tests/test_news_pipeline.py -v
```

Expected: PASS for the new plain-marker regression, existing fetch-error propagation tests, and any new spider print regression.

- [ ] **Step 4: Run the route contract tests for the news endpoint**

Run:

```bash
./env/bin/python -m pytest tests/test_routes.py -k news -v
```

Expected: PASS, proving the 500/502 contract is still intact after internal scraper changes.

### Task 4: Verify the complete repair and spot-check the live command

**Files:**
- No additional code changes expected

- [ ] **Step 1: Run the full unit suite**

Run:

```bash
./env/bin/python -m pytest -m unit -v
```

Expected: PASS for all unit tests.

- [ ] **Step 2: If the local API at `http://127.0.0.1:8020` is running, spot-check the live endpoint behavior**

Run:

```bash
curl -sS http://127.0.0.1:8020/api/v1/news/2026/April/
```

Expected: either a real news list or a stable fetch-error payload with `reason="challenge_detected"`; it should no longer flip to `missing_output` for the mixed-content case fixed above.

- [ ] **Step 3: Record the exact verification results in the final handoff**

Include:

```text
- plan path
- files changed
- targeted pytest commands and outcomes
- unit-suite outcome
- live endpoint outcome (if available)
- any remaining limitation (for example, genuine upstream Cloudflare blocking)
```
