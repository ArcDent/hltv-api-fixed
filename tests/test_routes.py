import json
from unittest.mock import Mock, patch


class TestRoutesEndpoints:
    """Tests for all API route endpoints."""

    def test_teams_ranking_endpoint(self, client, app):
        """Test teams ranking endpoint."""
        mock_data = {"teams": ["Natus Vincere", "Astralis", "FaZe Clan"]}

        with app.app_context():
            with patch("hltv_scraper.HLTVScraper._get_manager") as mock_get_manager:
                mock_manager = Mock()
                mock_manager.execute.return_value = None
                mock_manager.get_result.return_value = mock_data
                mock_get_manager.return_value = mock_manager

                response = client.get("/api/v1/teams/rankings")

                assert response.status_code == 200
                data = json.loads(response.data)
                assert isinstance(data, dict)
                assert data == mock_data

    def test_upcoming_matches_endpoint(self, client, app):
        """Test upcoming matches endpoint."""
        mock_data = {
            "matches": [{"team1": "NAVI", "team2": "Astralis", "date": "2023-08-30"}]
        }

        with app.app_context():
            with patch("hltv_scraper.HLTVScraper._get_manager") as mock_get_manager:
                mock_manager = Mock()
                mock_manager.execute.return_value = None
                mock_manager.get_result.return_value = mock_data
                mock_get_manager.return_value = mock_manager

                response = client.get("/api/v1/matches/upcoming")

                assert response.status_code == 200
                data = json.loads(response.data)
                assert isinstance(data, dict)
                assert data == mock_data

    def test_news_endpoint(self, client, app):
        """Test news endpoint."""
        mock_data = [{"title": "Major tournament announced", "date": "2023-08-30"}]

        with app.app_context():
            with patch("hltv_scraper.HLTVScraper._get_manager") as mock_get_manager:
                mock_manager = Mock()
                mock_manager.execute.return_value = None
                mock_manager.get_result.return_value = mock_data
                mock_get_manager.return_value = mock_manager

                response = client.get("/api/v1/news")

                assert response.status_code == 200
                data = json.loads(response.data)
                assert isinstance(data, list)
                assert data == mock_data

    def test_news_archive_endpoint_process_failure_contract(self, client, app):
        """Test news archive endpoint error contract for process failures."""
        with app.app_context():
            from hltv_scraper.errors import NewsScrapeProcessError

            with patch(
                "routes.news.HLTVScraper.get_news",
                side_effect=NewsScrapeProcessError(
                    "Scrapy execution failed for the news archive scrape.",
                    reason="process_failed",
                ),
            ):
                response = client.get("/api/v1/news/2026/April/")

                assert response.status_code == 500
                data = json.loads(response.data)
                assert data == {
                    "error": "news_scrape_failed",
                    "reason": "process_failed",
                    "message": "Scrapy execution failed for the news archive scrape.",
                    "year": 2026,
                    "month": "April",
                }

    def test_news_archive_endpoint_content_failure_contract(self, client, app):
        """Test news archive endpoint error contract for empty content failures."""
        with app.app_context():
            from hltv_scraper.errors import NewsScrapeContentError

            with patch(
                "routes.news.HLTVScraper.get_news",
                side_effect=NewsScrapeContentError(
                    "News scrape returned empty content for the requested archive period.",
                    reason="empty_content",
                ),
            ):
                response = client.get("/api/v1/news/2026/April/")

                assert response.status_code == 502
                data = json.loads(response.data)
                assert data == {
                    "error": "news_scrape_failed",
                    "reason": "empty_content",
                    "message": "News scrape returned empty content for the requested archive period.",
                    "year": 2026,
                    "month": "April",
                }

    def test_news_archive_endpoint_output_failure_contract(self, client, app):
        """Test news archive endpoint error contract for missing output failures."""
        with app.app_context():
            from hltv_scraper.errors import NewsScrapeOutputError

            with patch(
                "routes.news.HLTVScraper.get_news",
                side_effect=NewsScrapeOutputError(
                    "News scrape produced no output for the requested archive period.",
                    reason="missing_output",
                ),
            ):
                response = client.get("/api/v1/news/2026/April/")

                assert response.status_code == 502
                data = json.loads(response.data)
                assert data == {
                    "error": "news_scrape_failed",
                    "reason": "missing_output",
                    "message": "News scrape produced no output for the requested archive period.",
                    "year": 2026,
                    "month": "April",
                }

    def test_news_archive_endpoint_browser_timeout_failure_contract(self, client, app):
        with app.app_context():
            from hltv_scraper.errors import NewsScrapeFetchError

            with patch(
                "routes.news.HLTVScraper.get_news",
                side_effect=NewsScrapeFetchError(
                    "Browser fetch timed out while waiting for the news archive page.",
                    reason="browser_timeout",
                ),
            ):
                response = client.get("/api/v1/news/2026/April/")

                assert response.status_code == 502
                data = json.loads(response.data)
                assert data == {
                    "error": "news_scrape_failed",
                    "reason": "browser_timeout",
                    "message": "Browser fetch timed out while waiting for the news archive page.",
                    "year": 2026,
                    "month": "April",
                }

    def test_news_archive_endpoint_challenge_detected_failure_contract(
        self, client, app
    ):
        with app.app_context():
            from hltv_scraper.errors import NewsScrapeFetchError

            with patch(
                "routes.news.HLTVScraper.get_news",
                side_effect=NewsScrapeFetchError(
                    "News archive fetch is still blocked by a challenge page.",
                    reason="challenge_detected",
                ),
            ):
                response = client.get("/api/v1/news/2026/April/")

                assert response.status_code == 502
                data = json.loads(response.data)
                assert data == {
                    "error": "news_scrape_failed",
                    "reason": "challenge_detected",
                    "message": "News archive fetch is still blocked by a challenge page.",
                    "year": 2026,
                    "month": "April",
                }

    def test_results_endpoint(self, client, app):
        """Test results endpoint."""
        mock_data = {
            "results": [{"team1": "NAVI", "team2": "Astralis", "score": "16-14"}]
        }

        with app.app_context():
            with patch("hltv_scraper.HLTVScraper._get_manager") as mock_get_manager:
                mock_manager = Mock()
                mock_manager.execute.return_value = None
                mock_manager.get_result.return_value = mock_data
                mock_get_manager.return_value = mock_manager

                response = client.get("/api/v1/results/")

                assert response.status_code == 200
                data = json.loads(response.data)
                assert isinstance(data, dict)
                assert data == mock_data

    def test_player_search_success(self, client, app):
        """Test player search with successful result."""
        mock_data = {"player": "s1mple", "team": "NAVI", "rating": 1.25}

        with app.app_context():
            with patch("hltv_scraper.HLTVScraper._get_manager") as mock_get_manager:
                mock_manager = Mock()
                mock_manager.is_profile.return_value = True
                mock_manager.get_profile.return_value = mock_data
                mock_get_manager.return_value = mock_manager

                response = client.get("/api/v1/players/search/s1mple")

                assert response.status_code == 200
                data = json.loads(response.data)
                assert data == mock_data

    def test_player_search_not_found(self, client, app):
        """Test player search when player is not found."""
        with app.app_context():
            with patch("hltv_scraper.HLTVScraper._get_manager") as mock_get_manager:
                mock_manager = Mock()
                mock_manager.is_profile.return_value = False
                mock_get_manager.return_value = mock_manager

                response = client.get("/api/v1/players/search/nonexistent")

                assert response.status_code == 404
                data = json.loads(response.data)
                assert data == {"error": "Player not found!"}

    def test_team_search_success(self, client, app):
        """Test team search with successful result."""
        mock_data = {
            "team": "NAVI",
            "country": "Ukraine",
            "players": ["s1mple", "electronic"],
        }

        with app.app_context():
            with patch("hltv_scraper.HLTVScraper._get_manager") as mock_get_manager:
                mock_manager = Mock()
                mock_manager.is_profile.return_value = True
                mock_manager.get_profile.return_value = mock_data
                mock_get_manager.return_value = mock_manager

                response = client.get("/api/v1/teams/search/navi")

                assert response.status_code == 200
                data = json.loads(response.data)
                assert data == mock_data

    def test_team_search_not_found(self, client, app):
        """Test team search when team is not found."""
        with app.app_context():
            with patch("hltv_scraper.HLTVScraper._get_manager") as mock_get_manager:
                mock_manager = Mock()
                mock_manager.is_profile.return_value = False
                mock_get_manager.return_value = mock_manager

                response = client.get("/api/v1/teams/search/nonexistent")

                assert response.status_code == 404
                data = json.loads(response.data)
                assert data == {"error": "Team not found!"}
