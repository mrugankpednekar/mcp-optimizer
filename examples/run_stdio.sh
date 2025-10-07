#!/usr/bin/env bash
set -euo pipefail
uv run mcp dev src/mcp_optimizer/server.py "$@"
