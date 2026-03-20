from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    mongo_uri: str
    mongo_db: str
    mongo_max_result: int
    mcp: McpConfig


@dataclass(frozen=True)
class McpConfig:
    """
    MCP server transport configuration.

    This is used to expose the MCP server over HTTP/SSE so external clients
    (e.g., Cursor) can connect.
    """

    transport: str
    host: str
    port: int
    mount_path: str
    sse_path: str
    message_path: str


class PropertiesLoaderError(ValueError):
    """Raised when config.properties cannot be loaded or validated."""


def _parse_properties_file(config_path: Path) -> dict[str, str]:
    if not config_path.exists():
        raise PropertiesLoaderError(f"Config file not found: {config_path}")

    raw: dict[str, str] = {}
    for line_no, raw_line in enumerate(config_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()

        # Skip blank lines and comments
        if not line or line.startswith("#") or line.startswith(";"):
            continue

        if "=" not in line:
            raise PropertiesLoaderError(
                f"Invalid properties format at {config_path} line {line_no}: {raw_line!r}"
            )

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            raise PropertiesLoaderError(f"Empty key at {config_path} line {line_no}.")

        raw[key] = value

    return raw


def _require(raw: dict[str, str], key: str) -> str:
    if key not in raw:
        raise PropertiesLoaderError(
            f"Missing required config key {key!r}. Expected it in config file."
        )
    return raw[key]


def load_app_config(config_path: str | os.PathLike[str] = "config.properties") -> AppConfig:
    """
    Load and validate operational settings from a Java-style properties file.

    Required keys:
      - mongo.uri
      - mongo.db
      - mongo.maxResult
      - mcp.transport
      - mcp.host
      - mcp.port
      - mcp.mountPath
      - mcp.ssePath
      - mcp.messagePath
    """

    path = Path(config_path)
    raw = _parse_properties_file(path)

    mongo_uri = _require(raw, "mongo.uri")
    mongo_db = _require(raw, "mongo.db")
    max_result_raw = _require(raw, "mongo.maxResult")

    try:
        mongo_max_result = int(max_result_raw)
    except ValueError as e:
        raise PropertiesLoaderError(f"mongo.maxResult must be an integer: {max_result_raw!r}") from e

    if mongo_max_result <= 0:
        raise PropertiesLoaderError("mongo.maxResult must be > 0.")

    mcp_transport = _require(raw, "mcp.transport")
    mcp_host = _require(raw, "mcp.host")
    mcp_port_raw = _require(raw, "mcp.port")
    mcp_mount_path = _require(raw, "mcp.mountPath")
    mcp_sse_path = _require(raw, "mcp.ssePath")
    mcp_message_path = _require(raw, "mcp.messagePath")

    try:
        mcp_port = int(mcp_port_raw)
    except ValueError as e:
        raise PropertiesLoaderError(f"mcp.port must be an integer: {mcp_port_raw!r}") from e

    if mcp_port <= 0 or mcp_port > 65535:
        raise PropertiesLoaderError("mcp.port must be within 1..65535.")

    if not mcp_host.strip():
        raise PropertiesLoaderError("mcp.host must be a non-empty string.")

    # FastMCP requires these to be relative paths (SSE transport).
    for path_value, key in [(mcp_sse_path, "mcp.ssePath"), (mcp_message_path, "mcp.messagePath")]:
        if not path_value.startswith("/"):
            raise PropertiesLoaderError(f"{key} must start with '/'. Got: {path_value!r}")

    mcp_config = McpConfig(
        transport=mcp_transport,
        host=mcp_host,
        port=mcp_port,
        mount_path=mcp_mount_path,
        sse_path=mcp_sse_path,
        message_path=mcp_message_path,
    )

    return AppConfig(
        mongo_uri=mongo_uri,
        mongo_db=mongo_db,
        mongo_max_result=mongo_max_result,
        mcp=mcp_config,
    )


def app_config_from_env() -> AppConfig:
    """Optional convenience: load config from $CONFIG_PATH if set."""

    config_path = os.environ.get("CONFIG_PATH", "config.properties")
    return load_app_config(config_path=config_path)

