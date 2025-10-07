#!/usr/bin/env bash
set -euo pipefail
uv run mcp http src/mcp_optimizer/server.py --port 3333 --cors "*" "$@"
