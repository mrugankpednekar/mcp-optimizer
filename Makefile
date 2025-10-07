.PHONY: fmt lint test dev-http dev-stdio bench

fmt:
	black src tests scripts

lint:
	ruff check src tests scripts

test:
	pytest

dev-http:
	uv run mcp http src/mcp_optimizer/server.py --port 3333 --cors "*"

dev-stdio:
	uv run mcp dev src/mcp_optimizer/server.py

bench:
	python scripts/bench_lp.py
