from __future__ import annotations

import argparse
import anyio
import os
from pathlib import Path
from typing import Any

from config.config_loader import AppConfig, load_app_config
from db.mongo_client import MongoClientFactory
import modelcontextprotocol
from mcp.server.fastmcp import FastMCP
from tools.mongo_tools import MongoTools


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MCP MongoDB Server (HTTP/SSE or stdio).")
    parser.add_argument(
        "--config",
        dest="config_path",
        default=None,
        help="Path to config.properties (default: ./config.properties or $CONFIG_PATH).",
    )
    return parser.parse_args()


def _get_config_path(cli_config_path: str | None) -> str:
    # Only the file path is configurable; all operational values come from the properties file.
    base_dir = Path(__file__).resolve().parent
    if cli_config_path:
        return str(Path(cli_config_path).expanduser().resolve())
    env_path = os.environ.get("CONFIG_PATH")
    if env_path:
        return str(Path(env_path).expanduser().resolve())
    return str((base_dir / "config.properties").resolve())


def build_mcp_server(config: AppConfig) -> FastMCP:
    version = getattr(modelcontextprotocol, "__version__", "unknown")
    mcp_cfg = config.mcp
    mcp = FastMCP(
        name="mcp-mongo-server",
        instructions=(
            "MongoDB MCP server (FastMCP via modelcontextprotocol). "
            f"SDK version: {version}. "
            "Tools: mongo_find, mongo_insert, mongo_count, mongo_explain. "
            "Dangerous queries that include the $where operator are blocked."
        ),
        host=mcp_cfg.host,
        port=mcp_cfg.port,
        mount_path=mcp_cfg.mount_path,
        sse_path=mcp_cfg.sse_path,
        message_path=mcp_cfg.message_path,
    )

    client_factory = MongoClientFactory(config)
    mongo_tools = MongoTools(client_factory=client_factory, max_result=config.mongo_max_result)

    @mcp.tool()
    async def mongo_find(collection: str, query: dict[str, Any]) -> list[dict[str, Any]]:
        """Find documents in MongoDB (returns up to maxResult documents)."""
        return await anyio.to_thread.run_sync(mongo_tools.mongo_find, collection, query)

    @mcp.tool()
    async def mongo_insert(collection: str, document: dict[str, Any]) -> dict[str, Any]:
        """Insert one document into MongoDB and return insertion details."""
        return await anyio.to_thread.run_sync(mongo_tools.mongo_insert, collection, document)

    @mcp.tool()
    async def mongo_count(collection: str, query: dict[str, Any]) -> int:
        """Count documents in MongoDB matching the query."""
        return await anyio.to_thread.run_sync(mongo_tools.mongo_count, collection, query)

    @mcp.tool()
    async def mongo_explain(collection: str, query: dict[str, Any]) -> dict[str, Any]:
        """Return the MongoDB query execution plan for the given query."""
        return await anyio.to_thread.run_sync(mongo_tools.mongo_explain, collection, query)

    return mcp


def main() -> None:
    args = _parse_args()
    config_path = _get_config_path(args.config_path)
    config = load_app_config(config_path)

    mcp = build_mcp_server(config)
    mcp.run(transport=config.mcp.transport)


if __name__ == "__main__":
    main()

