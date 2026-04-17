import cloudscraper
from scrapy.http import HtmlResponse

from .browser_fetcher import BrowserHTMLFetcher
from .errors import NewsScrapeFetchError
from .response_factory import build_html_response


def _looks_like_challenge(html: str) -> bool:
    normalized = (html or "").lower()
    return any(
        marker in normalized
        for marker in (
            "just a moment...",
            "checking your browser before accessing",
            "cf-browser-verification",
            "attention required! | cloudflare",
        )
    )


def _looks_like_archive_content(html: str) -> bool:
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


def fetch_hltv_page(url: str) -> HtmlResponse:
    try:
        browser_result = BrowserHTMLFetcher().fetch(url)
        if _looks_like_challenge(browser_result.html):
            raise NewsScrapeFetchError(
                "Browser fetch reached a challenge page instead of the news archive page.",
                reason="challenge_detected",
            )
        if not _looks_like_archive_content(browser_result.html):
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

        if _looks_like_challenge(fallback_response.text):
            raise NewsScrapeFetchError(
                "News archive fetch is still blocked by a challenge page.",
                reason="challenge_detected",
            )

        if not _looks_like_archive_content(fallback_response.text):
            raise NewsScrapeFetchError(
                "Fallback fetch did not return expected news archive content.",
                reason="challenge_detected",
            )

        return build_html_response(fallback_response.url, fallback_response.text)
