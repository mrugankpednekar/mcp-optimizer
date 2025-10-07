#!/usr/bin/env sh
set -euo pipefail

MCP_CMD="mcp"

if command -v "$MCP_CMD" >/dev/null 2>&1; then
  exec "$MCP_CMD" http src/mcp_optimizer/server.py --host 0.0.0.0 --port 3333 --cors "*"
fi

if [ -d "/app/.venv/bin" ]; then
  exec /app/.venv/bin/python -m mcp_optimizer.server
fi

exec python -m mcp_optimizer.server
