import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from hltv_scraper import HLTVScraper
from hltv_scraper.cache_config import CACHE_HOURS_NEWS
from hltv_scraper.data import JsonDataLoader
from hltv_scraper.process import SpiderProcess
from hltv_scraper.spider_manager import SpiderManager


def test_spider_process_execute_strict_uses_current_python_and_raises_on_non_zero_exit():
    from hltv_scraper.errors import NewsScrapeProcessError

    process = Mock()
    process.wait.return_value = 1
    process.returncode = 1

    with patch(
        "hltv_scraper.process.subprocess.Popen", return_value=process
    ) as mock_popen:
        with pytest.raises(NewsScrapeProcessError) as exc_info:
            SpiderProcess().execute(
                "hltv_news",
                "/tmp",
                "-a year=2026 -a month=April -o data/news/news_2026_April.json",
                strict=True,
            )

    assert exc_info.value.reason == "process_failed"

    args, _kwargs = mock_popen.call_args
    assert args[0][0] == sys.executable


def test_json_data_loader_load_strict_raises_when_output_file_missing(tmp_path):
    from hltv_scraper.errors import NewsScrapeOutputError

    missing_output = tmp_path / "news_2026_April.json"

    with pytest.raises(NewsScrapeOutputError) as exc_info:
        JsonDataLoader().load(str(missing_output), strict=True)

    assert exc_info.value.reason == "missing_output"


def test_hltv_scraper_get_news_raises_content_error_when_manager_returns_empty_list():
    from hltv_scraper.errors import NewsScrapeContentError

    mock_manager = Mock()
    mock_manager.execute.return_value = None
    mock_manager.get_result.return_value = []

    with patch("hltv_scraper.HLTVScraper._get_manager", return_value=mock_manager):
        with pytest.raises(NewsScrapeContentError) as exc_info:
            HLTVScraper.get_news(2026, "April")

    assert exc_info.value.reason == "empty_content"


def test_hltv_scraper_get_news_reraises_manager_execute_process_error():
    from hltv_scraper.errors import NewsScrapeProcessError

    mock_manager = Mock()
    mock_manager.execute.side_effect = NewsScrapeProcessError(
        "process failed",
        reason="process_failed",
    )

    with patch("hltv_scraper.HLTVScraper._get_manager", return_value=mock_manager):
        with pytest.raises(NewsScrapeProcessError) as exc_info:
            HLTVScraper.get_news(2026, "April")

    assert exc_info.value.reason == "process_failed"


def test_hltv_scraper_get_news_reraises_manager_get_result_output_error():
    from hltv_scraper.errors import NewsScrapeOutputError

    mock_manager = Mock()
    mock_manager.execute.return_value = None
    mock_manager.get_result.side_effect = NewsScrapeOutputError(
        "output missing",
        reason="missing_output",
    )

    with patch("hltv_scraper.HLTVScraper._get_manager", return_value=mock_manager):
        with pytest.raises(NewsScrapeOutputError) as exc_info:
            HLTVScraper.get_news(2026, "April")

    assert exc_info.value.reason == "missing_output"


def test_hltv_scraper_get_news_propagates_strict_mode_to_manager_calls():
    mock_manager = Mock()

    with patch("hltv_scraper.HLTVScraper._get_manager", return_value=mock_manager):
        HLTVScraper.get_news(2026, "April")

    path = "news/news_2026_April"
    args = "-a year=2026 -a month=April -o data/news/news_2026_April.json"

    mock_manager.execute.assert_called_once_with(
        "hltv_news",
        path,
        args,
        CACHE_HOURS_NEWS,
        strict=True,
    )
    mock_manager.get_result.assert_called_once_with(path, strict=True)


def test_spider_manager_execute_forwards_strict_mode_to_spider_process(tmp_path):
    manager = SpiderManager(str(tmp_path))
    path = "news/news_2026_April"
    args = "-a year=2026 -a month=April -o data/news/news_2026_April.json"

    with patch.object(manager, "__should_run__", return_value=True):
        with patch("hltv_scraper.spider_manager.CF.get") as mock_cf_get:
            with patch(
                "hltv_scraper.spider_manager.SpiderProcess.execute"
            ) as mock_execute:
                condition = Mock()
                condition.check.return_value = False
                mock_cf_get.return_value = condition

                manager.execute("hltv_news", path, args, strict=True)

    mock_execute.assert_called_once_with("hltv_news", str(tmp_path), args, strict=True)


def test_spider_manager_get_result_forwards_strict_mode_to_json_loader(tmp_path):
    manager = SpiderManager(str(tmp_path))
    manager.loader = Mock(spec=JsonDataLoader)
    manager.loader.load.return_value = []

    manager.get_result("news/news_2026_April", strict=True)

    manager.loader.load.assert_called_once_with(
        manager.path.generate("news/news_2026_April"),
        strict=True,
    )


def test_news_parser_imports_from_scrapy_cwd_package_layout():
    repo_root = Path(__file__).resolve().parents[1]
    scrapy_cwd = repo_root / "hltv_scraper"

    import_result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from hltv_scraper.spiders.parsers.news "
                "import NewsParser; "
                "from hltv_scraper.errors import NewsScrapeContentError; "
                "print(NewsParser.__name__, NewsScrapeContentError.__name__)"
            ),
        ],
        cwd=scrapy_cwd,
        capture_output=True,
        text=True,
        check=False,
    )

    assert import_result.returncode == 0, import_result.stderr
