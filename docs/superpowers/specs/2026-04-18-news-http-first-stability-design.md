# News HTTP-First Stability Design

## Goal

Make `/api/v1/news` default requests return real news content most of the time by treating successful extraction of article data as the success condition, instead of treating “not obviously blocked HTML” as success.

## Current Problem

The current news path is browser-first and only falls back to `cloudscraper` for browser setup/timeouts. In practice, HLTV news archive responses fluctuate between:

- full archive HTML containing parseable `NewsArticle` data and Cloudflare script markers,
- and hard challenge/403 pages.

That means the system needs to exploit occasional successful HTTP fetch windows, not just classify blocked pages more accurately.

## Design Summary

Replace the current browser-first news fetch flow with an HTTP-first orchestration layer:

1. Try a browser-like HTTP session first.
2. Validate candidates by attempting to extract news articles.
3. If the HTTP session cannot produce parseable content, try the browser strategy.
4. If the browser strategy fails, retry the HTTP session with a fresh session.
5. Raise the last meaningful fetch error only after all strategies fail.

The fetch layer stays responsible for delivering only parseable archive HTML to the spider. The spider/parser contracts remain unchanged at the route level.

## Components

### 1. `news_http_fetcher.py`

New helper responsible for HTTP-session fetching with:

- `cloudscraper.create_scraper(...)`
- browser-like headers
- homepage warm-up request to `https://www.hltv.org/`
- archive-page request to the requested month/year URL
- conversion to `HtmlResponse`

This module returns candidate HTML, not final success. Success is decided by content extraction.

### 2. `news_content.py`

New shared extraction module containing the reusable article extraction logic currently embedded in `NewsParser`:

- CSS extraction from `a.newsline.article`
- JSON-LD extraction for `NewsArticle`
- result normalization into the existing article dict shape

Both the fetch orchestration layer and `NewsParser` will use this shared extractor.

### 3. `challenge_fetcher.py`

Refactor from “browser-first challenge detector” into “multi-strategy news fetch orchestrator”.

Responsibilities:

- try HTTP session candidate first,
- reject hard blocked pages using `is_blocked_archive_page(...)`,
- accept only candidates that produce at least one extracted article,
- try browser strategy second,
- try one final fresh HTTP session retry third,
- preserve the last meaningful `NewsScrapeFetchError` reason/message.

### 4. `NewsParser`

Keep `NewsParser.parse(response)` as the route-facing parser, but make it reuse the shared extractor instead of duplicating CSS/JSON-LD parsing logic.

The parser should still:

- raise `NewsScrapeContentError` for truly blocked pages,
- raise `NewsScrapeContentError` when no parseable articles exist,
- return article dicts in the existing shape.

## Success Criteria

The new success rule is:

> A fetch strategy succeeds only if it yields at least one parsed news article.

This is stronger than marker-based heuristics and directly matches the user requirement of “stable content retrieval”.

## Error Handling

- Keep existing route status behavior:
  - `NewsScrapeProcessError` -> 500
  - `NewsScrapeFetchError`, `NewsScrapeContentError`, `NewsScrapeOutputError` -> 502
- Keep `HLTV_NEWS_FETCH_REASON:<reason>:<message>` stderr emission in the spider.
- Reuse existing `reason` values where possible to avoid unnecessary contract churn:
  - `challenge_detected`
  - `browser_timeout`
  - `browser_fetch_failed`
  - `fallback_failed`

## Testing Strategy

1. Add failing tests for HTTP-first orchestration.
2. Add failing tests for “parseable content means success”.
3. Add regression coverage ensuring browser is skipped when HTTP already produced parseable articles.
4. Keep existing route-contract and strict-marker tests green.
5. Run scoped suites plus a live spot-check against a local server started from the worktree.

## Constraints

- Do not change route JSON structure or status-code mapping.
- Do not rely on a background cache refresh system for this task.
- Keep the existing spider/subprocess path intact; improve the fetch strategy within that path.
