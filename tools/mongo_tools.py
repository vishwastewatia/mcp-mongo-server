from __future__ import annotations

import re
from typing import Any

from bson import json_util
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from db.mongo_client import MongoClientFactory


class MongoToolError(ValueError):
    """Raised when validation fails for a MongoDB tool input."""


FORBIDDEN_QUERY_KEYS = {"$where"}
_COLLECTION_NAME_RE = re.compile(r"^[A-Za-z0-9_.\-]+$")


def _to_json_serializable(value: Any) -> Any:
    """
    Convert Mongo/BSON types (ObjectId, datetime, Decimal128, etc.) into JSON-safe structures.
    """

    # json_util.dumps produces JSON, then loads converts it into plain Python objects.
    return json_util.loads(json_util.dumps(value))


def _contains_forbidden_keys(payload: Any) -> bool:
    """
    Recursively scan for forbidden Mongo operators.

    This blocks injection vectors such as {$where: "..."}.
    """

    if isinstance(payload, dict):
        for key, val in payload.items():
            if key in FORBIDDEN_QUERY_KEYS:
                return True
            if _contains_forbidden_keys(val):
                return True
        return False

    if isinstance(payload, list):
        return any(_contains_forbidden_keys(item) for item in payload)

    return False


def _validate_collection_name(collection: str) -> None:
    if not isinstance(collection, str) or not collection.strip():
        raise MongoToolError("`collection` must be a non-empty string.")

    collection = collection.strip()
    if len(collection) > 255:
        raise MongoToolError("`collection` is too long.")

    # Basic safety: block system collections and obviously suspicious names.
    if collection.startswith("system."):
        raise MongoToolError("Access to `system.*` collections is not allowed.")

    if "\x00" in collection:
        raise MongoToolError("Invalid `collection` name.")

    if not _COLLECTION_NAME_RE.match(collection):
        raise MongoToolError("`collection` contains invalid characters.")


def _validate_query_object(query: Any) -> dict[str, Any]:
    if not isinstance(query, dict):
        raise MongoToolError("`query` must be a JSON object (dict).")
    if _contains_forbidden_keys(query):
        raise MongoToolError("Forbidden Mongo operator detected: `$where`.")
    return query


def _validate_document_object(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise MongoToolError("`document` must be a JSON object (dict).")
    if _contains_forbidden_keys(document):
        raise MongoToolError("Forbidden Mongo operator detected in document: `$where`.")
    return document


class MongoTools:
    """
    Thin, validated wrapper around MongoDB operations.

    All methods return JSON-serializable Python objects.
    """

    def __init__(self, *, client_factory: MongoClientFactory, max_result: int):
        self._db = client_factory.get_database()
        self._max_result = max_result

    def _collection(self, collection: str) -> Collection:
        _validate_collection_name(collection)
        return self._db[collection]

    def mongo_find(self, collection: str, query: dict[str, Any]) -> list[dict[str, Any]]:
        col = self._collection(collection)
        query = _validate_query_object(query)

        try:
            cursor = col.find(query).limit(self._max_result)
            docs = list(cursor)
            return [_to_json_serializable(doc) for doc in docs]
        except PyMongoError as e:
            raise RuntimeError(f"MongoDB find failed: {str(e)}") from e

    def mongo_insert(self, collection: str, document: dict[str, Any]) -> dict[str, Any]:
        col = self._collection(collection)
        document = _validate_document_object(document)

        try:
            result = col.insert_one(document)
            return {
                "acknowledged": bool(result.acknowledged),
                "insertedId": _to_json_serializable(result.inserted_id),
            }
        except PyMongoError as e:
            raise RuntimeError(f"MongoDB insert failed: {str(e)}") from e

    def mongo_count(self, collection: str, query: dict[str, Any]) -> int:
        col = self._collection(collection)
        query = _validate_query_object(query)

        try:
            return int(col.count_documents(query))
        except PyMongoError as e:
            raise RuntimeError(f"MongoDB count failed: {str(e)}") from e

    def mongo_explain(self, collection: str, query: dict[str, Any]) -> dict[str, Any]:
        col = self._collection(collection)
        query = _validate_query_object(query)

        try:
            cursor = col.find(query).limit(self._max_result)
            plan = cursor.explain()
            return _to_json_serializable(plan)
        except PyMongoError as e:
            raise RuntimeError(f"MongoDB explain failed: {str(e)}") from e

