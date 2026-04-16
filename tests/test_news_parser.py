import pytest
from scrapy.http import HtmlResponse, Request

from hltv_scraper.errors import NewsScrapeContentError
from hltv_scraper.hltv_scraper.spiders.parsers.news import NewsParser


def _response_from_html(
    html: str, url: str = "https://www.hltv.org/news/archive/2026/April"
) -> HtmlResponse:
    request = Request(url=url)
    return HtmlResponse(
        url=url, request=request, body=html.encode("utf-8"), encoding="utf-8"
    )


def test_news_parser_parses_css_newsline_article_entries():
    response = _response_from_html(
        """
        <html>
          <body>
            <a class="newsline article" href="/news/123/example-news">
              <img class="newsflag" src="https://img.hltv.org/flag.png" />
              <div class="newstext">Example title</div>
              <div class="newsrecent">2026-04-11</div>
              <div class="newstc"><div></div><div>15</div></div>
            </a>
          </body>
        </html>
        """
    )

    parsed = NewsParser.parse(response)

    assert parsed == [
        {
            "title": "Example title",
            "img": "https://img.hltv.org/flag.png",
            "date": "2026-04-11",
            "comments": "15",
            "link": "https://www.hltv.org/news/123/example-news",
        }
    ]


def test_news_parser_falls_back_to_jsonld_news_article_entries():
    response = _response_from_html(
        """
        <html>
          <body>
            <script type="application/ld+json">
              {
                "@context": "https://schema.org",
                "@graph": [
                  {"@type": "BreadcrumbList", "name": "ignored"},
                  {
                    "@type": "NewsArticle",
                    "headline": "JSON-LD title",
                    "image": "https://img.hltv.org/jsonld.png",
                    "datePublished": "2026-04-10T00:00:00Z",
                    "url": "https://www.hltv.org/news/100/jsonld-title"
                  }
                ]
              }
            </script>
          </body>
        </html>
        """
    )

    parsed = NewsParser.parse(response)

    assert parsed == [
        {
            "title": "JSON-LD title",
            "img": "https://img.hltv.org/jsonld.png",
            "date": "2026-04-10T00:00:00Z",
            "comments": None,
            "link": "https://www.hltv.org/news/100/jsonld-title",
        }
    ]


def test_news_parser_falls_back_to_jsonld_itemlist_news_article_entries():
    response = _response_from_html(
        """
        <html>
          <body>
            <script type="application/ld+json">
              {
                "@context": "https://schema.org",
                "@type": "ItemList",
                "itemListElement": [
                  {
                    "@type": "ListItem",
                    "position": 1,
                    "item": {
                      "@type": "NewsArticle",
                      "headline": "Nested item title",
                      "image": "https://img.hltv.org/nested.png",
                      "datePublished": "2026-04-12T10:00:00Z",
                      "commentCount": 27,
                      "url": "https://www.hltv.org/news/200/nested-item-title"
                    }
                  }
                ]
              }
            </script>
          </body>
        </html>
        """
    )

    parsed = NewsParser.parse(response)

    assert parsed == [
        {
            "title": "Nested item title",
            "img": "https://img.hltv.org/nested.png",
            "date": "2026-04-12T10:00:00Z",
            "comments": 27,
            "link": "https://www.hltv.org/news/200/nested-item-title",
        }
    ]


def test_news_parser_falls_back_to_jsonld_news_article_image_object_list():
    response = _response_from_html(
        """
        <html>
          <body>
            <script type="application/ld+json">
              {
                "@context": "https://schema.org",
                "@type": "NewsArticle",
                "headline": "Image object list title",
                "image": [
                  {"url": "https://img.hltv.org/example.png"}
                ],
                "datePublished": "2026-04-13T00:00:00Z",
                "url": "https://www.hltv.org/news/300/image-object-list"
              }
            </script>
          </body>
        </html>
        """
    )

    parsed = NewsParser.parse(response)

    assert parsed == [
        {
            "title": "Image object list title",
            "img": "https://img.hltv.org/example.png",
            "date": "2026-04-13T00:00:00Z",
            "comments": None,
            "link": "https://www.hltv.org/news/300/image-object-list",
        }
    ]


def test_news_parser_raises_content_error_for_challenge_pages():
    response = _response_from_html(
        """
        <html>
          <head><title>Just a moment...</title></head>
          <body>Checking your browser before accessing</body>
        </html>
        """
    )

    with pytest.raises(NewsScrapeContentError):
        NewsParser.parse(response)
