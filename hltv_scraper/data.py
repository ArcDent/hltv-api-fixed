from abc import ABC, abstractmethod
import json
import os

from .errors import NewsScrapeOutputError


class DataLoader(ABC):
    @abstractmethod
    def load(self, file: str) -> dict:
        pass


class JsonDataLoader(DataLoader):
    def load(self, file: str, strict: bool = False) -> dict:
        if not os.path.exists(file):
            if strict:
                raise NewsScrapeOutputError(
                    "News scrape produced no output for the requested archive period."
                )
            return {}

        try:
            with open(file, "r", encoding="utf-8") as json_file:
                return json.load(json_file)
        except UnicodeDecodeError as e:
            if strict:
                raise NewsScrapeOutputError(
                    "News scrape output file is not valid UTF-8 for the requested archive period.",
                    reason="invalid_encoding",
                ) from e
            print(f"Error loading JSON file {file}: {e}")
            return {}
        except json.JSONDecodeError as e:
            if strict:
                raise NewsScrapeOutputError(
                    "News scrape output file is not valid JSON for the requested archive period.",
                    reason="invalid_json",
                ) from e
            print(f"Error loading JSON file {file}: {e}")
            return {}
        except Exception as e:
            if strict:
                raise NewsScrapeOutputError(
                    "News scrape produced no output for the requested archive period."
                ) from e
            print(f"Error loading JSON file {file}: {e}")
            return {}
