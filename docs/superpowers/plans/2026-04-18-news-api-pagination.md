# News API Pagination Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a backward-compatible paginated mode to the upstream news API and write an MCP follow-up reference document without changing the MCP codebase.

**Architecture:** Keep the existing raw-array success contract for legacy callers, and enable paginated mode on the same news routes when `limit` and/or `offset` query parameters are present. Put slicing and metadata generation in `HLTVScraper`, keep `routes/news.py` thin, and document the future MCP-side work in a separate markdown file.

**Tech Stack:** Python 3.13, Flask, Scrapy, pytest, Flasgger YAML docs

---

## File Structure

- Create: `docs/superpowers/specs/2026-04-18-news-api-pagination-design.md`
- Create: `docs/superpowers/specs/2026-04-18-mcp-news-followup-reference.md`
- Create: `docs/superpowers/plans/2026-04-18-news-api-pagination.md`
- Modify: `hltv_scraper/__init__.py`
- Modify: `routes/news.py`
- Modify: `tests/test_routes.py`
- Modify: `swagger_specs/news_list.yml`

### Task 1: Add failing route tests for paginated news mode

**Files:**
- Modify: `tests/test_routes.py`

- [ ] **Step 1: Add a failing test for `?limit=50` returning pagination metadata**

Add a route test that patches `routes.news.HLTVScraper.get_news_page` to return a pagination envelope and asserts `GET /api/v1/news?limit=50` returns a `200` object containing `items`, `total`, `count`, `limit`, `offset`, `has_more`, `next_offset`, `year`, and `month`.

- [ ] **Step 2: Run the new paginated-mode route test and verify it fails**

Run: `./env/bin/python -m pytest tests/test_routes.py -k news_endpoint_pagination -v`

Expected: FAIL because the route does not yet parse pagination parameters or call a paginated scraper method.

- [ ] **Step 3: Add a failing test for non-zero offset paging**

Add a route test that patches `routes.news.HLTVScraper.get_news_page`, requests `GET /api/v1/news/2026/April/?limit=2&offset=2`, and asserts the route returns the later page with the correct pagination metadata.

- [ ] **Step 4: Run the offset pagination test and verify it fails**

Run: `./env/bin/python -m pytest tests/test_routes.py -k news_endpoint_offset_pagination -v`

Expected: FAIL because the route currently ignores pagination query parameters.

- [ ] **Step 5: Add a failing test for invalid pagination input**

Add a route test asserting `GET /api/v1/news?limit=0` returns `400` with:

```json
{
  "error": "invalid_pagination",
  "message": "Query parameter 'limit' must be a positive integer."
}
```

- [ ] **Step 6: Run the invalid-pagination test and verify it fails**

Run: `./env/bin/python -m pytest tests/test_routes.py -k invalid_pagination -v`

Expected: FAIL because the route currently accepts no pagination validation path.

### Task 2: Implement upstream paginated news helper and route parsing

**Files:**
- Modify: `hltv_scraper/__init__.py`
- Modify: `routes/news.py`

- [ ] **Step 1: Add `HLTVScraper.get_news_page(...)`**

Implement a helper in `hltv_scraper/__init__.py` with the signature:

```python
@staticmethod
def get_news_page(year: int, month: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
```

The method should:

1. call `HLTVScraper.get_news(year, month)`
2. compute `total = len(data)`
3. slice `items = data[offset:offset + limit]`
4. compute `count`, `has_more`, and `next_offset`
5. return the pagination envelope including `year` and `month`

- [ ] **Step 2: Update `routes/news.py` to support opt-in paginated mode**

Implement route behavior:

1. if neither `limit` nor `offset` is present, keep legacy array behavior via `HLTVScraper.get_news(...)`
2. if either query param is present, parse and validate both values (`limit` default 50, `offset` default 0)
3. invalid values return `400` with `invalid_pagination`
4. valid values call `HLTVScraper.get_news_page(...)`
5. preserve the existing 500/502 exception mapping for scrape failures

- [ ] **Step 3: Run the new pagination-focused route tests and verify they pass**

Run: `./env/bin/python -m pytest tests/test_routes.py -k "news_endpoint_pagination or news_endpoint_offset_pagination or invalid_pagination" -v`

Expected: PASS.

- [ ] **Step 4: Run the existing news route contract tests and verify they stay green**

Run: `./env/bin/python -m pytest tests/test_routes.py -k news -v`

Expected: PASS, including the legacy array response test and all 500/502 error-contract tests.

### Task 3: Update Swagger docs and MCP follow-up reference

**Files:**
- Modify: `swagger_specs/news_list.yml`
- Create: `docs/superpowers/specs/2026-04-18-mcp-news-followup-reference.md`

- [ ] **Step 1: Update `swagger_specs/news_list.yml` for pagination query params**

Document query parameters:

- `limit` (query, positive integer)
- `offset` (query, non-negative integer)

Document that `200` may be either:

- the legacy news array, or
- a paginated object when pagination query params are used.

- [ ] **Step 2: Write the MCP follow-up reference markdown file**

Create the reference file with:

1. the future upstream call pattern (`?limit=50&offset=0`)
2. required future MCP news-rendering work
3. agreed dual-name team mapping guidance
4. explicit note that `PariVision -> PV` and `paiN != PV`

- [ ] **Step 3: Verify docs contain no placeholders**

Run: `python3 - <<'PY'
from pathlib import Path
paths = [
    Path('docs/superpowers/specs/2026-04-18-news-api-pagination-design.md'),
    Path('docs/superpowers/specs/2026-04-18-mcp-news-followup-reference.md'),
    Path('docs/superpowers/plans/2026-04-18-news-api-pagination.md'),
    Path('swagger_specs/news_list.yml'),
]
bad = []
forbidden_tokens = [
    'TB' + 'D',
    'TO' + 'DO',
    'implement' + ' later',
    'fill in' + ' details',
]
for path in paths:
    text = path.read_text()
    if any(token in text for token in forbidden_tokens):
        bad.append(str(path))
print('OK' if not bad else '\n'.join(bad))
PY`

Expected: `OK`.

### Task 4: Final verification and live API check

**Files:**
- Test: `tests/test_routes.py`

- [ ] **Step 1: Run the full route suite**

Run: `./env/bin/python -m pytest tests/test_routes.py -v`

Expected: PASS with zero failures.

- [ ] **Step 2: Run the broader news-related regression suite**

Run: `./env/bin/python -m pytest tests/test_browser_fetcher.py tests/test_news_parser.py tests/test_news_pipeline.py tests/test_routes.py -q`

Expected: PASS.

- [ ] **Step 3: Live-check the new paginated API mode**

Run: `./env/bin/python -c "from app import create_app; app = create_app(); app.run(host='127.0.0.1', port=8011)" >/tmp/news_api_8011.log 2>&1 & pid=$!; sleep 5; curl -sS -i "http://127.0.0.1:8011/api/v1/news/2026/April/?limit=50&offset=0"; status=$?; kill $pid; wait $pid || true; exit $status`

Expected: `200` with a paginated object containing `items`, `total`, `limit`, `offset`, and `has_more`, or the existing `500/502` error contract if the upstream scrape is actively blocked.

- [ ] **Step 4: Report exact outcomes honestly**

Summarize:

- route-test results
- broader news-regression results
- live paginated-route response
- the fact that MCP code was intentionally not changed in this task

Do not create commits unless the user explicitly asks.
