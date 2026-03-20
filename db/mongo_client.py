from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pymongo import MongoClient

from config.config_loader import AppConfig


@dataclass(frozen=True)
class MongoClientConfig:
    mongo_uri: str
    mongo_db: str


class MongoClientFactory:
    """
    Creates and holds a shared pymongo MongoClient instance.

    pymongo clients are designed to be long-lived and thread-safe.
    """

    def __init__(self, config: AppConfig):
        self._config = MongoClientConfig(mongo_uri=config.mongo_uri, mongo_db=config.mongo_db)
        self._client = MongoClient(self._config.mongo_uri)

    def get_database(self) -> Any:
        """Return the configured database handle."""
        return self._client[self._config.mongo_db]

    def close(self) -> None:
        """Close the underlying pymongo client."""
        self._client.close()

