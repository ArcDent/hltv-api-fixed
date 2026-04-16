import subprocess
import sys
from abc import ABC, abstractmethod

from .errors import NewsScrapeProcessError


class Process(ABC):
    @abstractmethod
    def execute(self, *args, **kwargs) -> None:
        pass


class SpiderProcess(Process):
    def execute(
        self, spider_name: str, dir: str, args: str, strict: bool = False
    ) -> None:
        process = subprocess.Popen(
            [sys.executable, "-m", "scrapy", "crawl", spider_name] + args.split(),
            cwd=dir,
        )
        return_code = process.wait()

        if strict and return_code != 0:
            raise NewsScrapeProcessError(
                "Scrapy execution failed for the news archive scrape."
            )
