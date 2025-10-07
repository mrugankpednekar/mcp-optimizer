#!/usr/bin/env sh
set -euo pipefail
exec mcp http src/crew_optimizer/server.py --host 0.0.0.0 --port 3333 --cors "*"
