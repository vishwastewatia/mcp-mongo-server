# MCP MongoDB Server

This repository contains a production-quality Model Context Protocol (MCP) server in Python that exposes MongoDB operations as MCP tools.

## Requirements

- Python 3.10+
- MongoDB running locally (by default)

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Ensure MongoDB is reachable.
   - Configuration is loaded from `config.properties` at the project root.
   - You can override the config path via `CONFIG_PATH` or `python main.py --config /path/to/config.properties`.

3. Run the MCP server:

```bash
python main.py
```

## MCP Tools

Tools are exposed based on `mcp.transport` in `config.properties`.

By default, this project runs MCP over **HTTP/SSE** so you can connect it from external MCP clients like Cursor.

Available tools:

- `mongo_find(collection: str, query: dict)`
- `mongo_insert(collection: str, document: dict)`
- `mongo_count(collection: str, query: dict)`
- `mongo_explain(collection: str, query: dict)`

## Example Usage

From any MCP client, call a tool by name with JSON arguments.

Example: find documents in the `users` collection:

```json
{
  "tool": "mongo_find",
  "arguments": {
    "collection": "users",
    "query": { "status": "active" }
  }
}
```

Notes:

- `mongo_find` limits returned documents using `mongo.maxResult` from `config.properties`.
- The server blocks dangerous queries containing the MongoDB `$where` operator.

## Connect Endpoint (SSE)

When `mcp.transport=sse`, the MCP SSE endpoint is:

`http://127.0.0.1:8000/sse`

Use this URL in your MCP client configuration (Cursor or other MCP clients).
