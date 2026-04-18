# News API Pagination Design

## Goal

Add a news-pagination capability to the upstream Flask API so future MCP work can request the first 50 items, know the total count, and continue from later offsets without re-scraping or reimplementing paging logic client-side.

## Scope

This change is intentionally limited to the API repository:

- implement upstream news pagination and metadata support in `hltv-api-fixed`
- keep the current news scrape/error pipeline intact
- write a separate MCP follow-up reference document in this repository
- do **not** modify the MCP codebase in this task

## Current Problem

`/api/v1/news` currently returns a raw JSON array on success. That is enough for simple consumers, but it does not expose:

- total item count
- offset/limit information
- whether more pages remain
- a stable upstream contract for “first 50, then continue” behavior

At the same time, the current MCP client still expects the legacy array response, so a hard breaking change to the default success shape would create avoidable churn before the MCP conversation happens.

## Design Summary

Keep the current success response untouched for legacy callers, and add an opt-in paginated mode through query parameters on the same route.

Behavior:

1. `GET /api/v1/news` and `GET /api/v1/news/<year>/<month>/` without pagination query params keep returning the legacy raw array.
2. If either `limit` or `offset` is present, the route switches to paginated mode.
3. Paginated mode returns an object containing sliced items plus pagination metadata.
4. The default page size in paginated mode is `50` when `limit` is omitted.
5. `offset` defaults to `0` when omitted.

This lets the future MCP layer call the upstream API with `?limit=50&offset=0` while preserving compatibility for current array-based consumers.

## Route Contract

### Legacy mode

Unchanged:

- success: raw array of news items
- `NewsScrapeProcessError` -> `500`
- `NewsScrapeFetchError` / `NewsScrapeContentError` / `NewsScrapeOutputError` -> `502`

### Paginated mode

Success response shape:

```json
{
  "items": [
    {
      "title": "...",
      "date": "2026-04-18",
      "comments": "27 comments",
      "link": "https://www.hltv.org/news/...",
      "img": "/img/..."
    }
  ],
  "total": 176,
  "count": 50,
  "limit": 50,
  "offset": 0,
  "has_more": true,
  "next_offset": 50,
  "year": 2026,
  "month": "April"
}
```

Field meanings:

- `items`: sliced page payload
- `total`: total articles in the fetched archive list
- `count`: number of returned items in this page
- `limit`: applied page size
- `offset`: applied offset
- `has_more`: whether another page exists after this one
- `next_offset`: next offset when `has_more` is true, else `null`
- `year`, `month`: resolved archive parameters used by the route

### Invalid query parameters

Return `400` for invalid pagination input:

- non-integer `limit` / `offset`
- `limit <= 0`
- `offset < 0`

Suggested error shape:

```json
{
  "error": "invalid_pagination",
  "message": "Query parameter 'limit' must be a positive integer."
}
```

## Architecture

### 1. Keep the route thin

`routes/news.py` should only:

- resolve default year/month values
- parse and validate pagination query params
- choose legacy or paginated scraper method
- preserve existing exception mapping

### 2. Add upstream pagination helper to `HLTVScraper`

Add a helper such as `HLTVScraper.get_news_page(year, month, limit=50, offset=0)` that:

1. calls the existing `HLTVScraper.get_news(year, month)`
2. computes `total`
3. slices the list with `offset:offset+limit`
4. returns the pagination envelope

This keeps route logic small and localizes the pagination behavior near the scraper facade.

### 3. Swagger must match the route

`swagger_specs/news_list.yml` needs query parameter docs for `limit` and `offset`, plus a success schema description that explains the route can return either:

- the legacy array, or
- the paginated object when paging params are present

## Constraints

- Do not change the scrape pipeline or news fetcher in this task.
- Do not change the current 500/502 split.
- Do not modify the MCP repo in this task.
- Keep the current route usable by legacy callers.

## Testing Strategy

1. Add a red route test for paginated mode returning metadata and sliced items.
2. Add a red route test for non-zero offset paging.
3. Add a red route test for invalid `limit` and/or `offset` returning `400`.
4. Keep the existing legacy-array success test green.
5. Keep the existing error-contract tests green.
6. Run the scoped route suite plus a live route spot-check if needed.
