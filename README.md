# MCP Optimizer

MCP Optimizer is an MCP server that exposes linear (LP) and mixed-integer (MILP) optimization tooling through the official MCP Python SDK. It ships a readable primal simplex implementation (with duals), a tiny branch-and-cut MILP solver with optional OR-Tools fallback, and helper utilities such as a natural-language LP parser, infeasibility diagnostics, examples, tests, Docker packaging, and CI.

## Quickstart

```sh
# if uv available (preferred)
uv init mcp-optimizer && cd mcp-optimizer
# (if this is already a plain folder, skip the init and just create files)

# write all files above, then:
uv add "mcp[cli]" numpy scipy pydantic
uv add --dev pytest ruff black
# optional MILP fallback:
uv add --optional mip ortools

# stdio dev (MCP Inspector)
uv run mcp dev src/mcp_optimizer/server.py

# streamable HTTP (for Smithery remote testing)
uv run mcp http src/mcp_optimizer/server.py --port 3333 --cors "*"
```

If `uv` is not available, the equivalent `pip` workflow is:

```sh
python -m venv .venv && source .venv/bin/activate
pip install "mcp[cli]" numpy scipy pydantic pytest ruff black
```

Install the package in editable mode (optional but handy):

```sh
pip install -e .
```

## Local Development

- `make fmt` – format with Black
- `make lint` – Ruff lint
- `make test` – run pytest test-suite (covers simplex optimality, duals, and MILP branch-and-cut)
- `make dev-stdio` / `make dev-http` – run the MCP server via FastMCP over stdio or HTTP
- `make bench` – quick benchmarking over the bundled toy instances

The repo includes `scripts/generate_instances.py` to craft random feasible LPs for experimentation and `scripts/bench_lp.py` to profile solver iterations and timing.

## Tools Exposed

`src/mcp_optimizer/server.py` registers the following MCP tools:

- `solve_lp(model, options?)` – primal simplex (Phase I/II, Bland pivot fallback, duals & reduced costs)
- `solve_mip(model, use_or_tools=False, options?)` – depth-first branch-and-cut with bound tightening and optional OR-Tools CBC fallback
- `parse_nl_to_lp(spec)` – small rule-based parser for toy natural language LP descriptions
- `analyze_infeasibility(model)` – IIS-style diagnostic by constraint removal heuristics

Schemas live in `src/mcp_optimizer/schemas.py` (Pydantic models). Example payloads are available under `examples/` and in `examples/call_tools.http`.

## Running Examples

```sh
# stdio transport
./examples/run_stdio.sh

# HTTP transport (default port 3333)
./examples/run_http.sh

# Invoke from HTTP client
http --json :3333/tools/solve_lp < examples/call_tools.http
```

## Docker & Compose

```sh
docker build -t mcp-optimizer:latest -f docker/Dockerfile .
docker run --rm -p 3333:3333 mcp-optimizer:latest
```

`docker/compose.yaml` mirrors the same configuration for local orchestration.

## Continuous Integration

`.github/workflows/ci.yml` runs Ruff, Black, pytest, and builds the Docker image on every push/PR to `main`.

## Deployment via Smithery

1. Ensure the GitHub repository is public and contains the bundled `smithery.json` manifest.
2. From Smithery, choose **Publish an MCP Server** → **Continue with GitHub**, select the repository, and confirm the entry command `python -m mcp_optimizer.server`.
3. Verify installation from the Smithery catalog, then connect from ChatGPT/Claude MCP clients over HTTP (port 3333) or stdio.

## Benchmarks & Limitations

The simplex solver targets readability over raw speed; it is appropriate for classroom-sized problems (tens of variables/constraints). Branch-and-cut is intentionally simple (no advanced cuts beyond bound tightening) and explores nodes depth-first with a soft limit; use the OR-Tools fallback for larger MILPs. Numerical stability is managed with tolerances but may require tuning (`SolveOptions.tol`) for ill-conditioned models.

## License

Distributed under the MIT License. See `LICENSE` for full text.
