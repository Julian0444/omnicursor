"""MCP server exposing Omnimarket bridge tools to Cursor."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from omnicursor import omnimarket_bridge

mcp = FastMCP("omnicursor-omnimarket")


@mcp.tool(
    description=(
        "Run Omnimarket node_local_review via subprocess against a local checkout. "
        "Requires OMNIMARKET_ROOT env var or omnimarket-main/ in repo root."
    ),
)
def run_local_review(
    dry_run: bool = True,
    max_iterations: int = 10,
    required_clean_runs: int = 2,
) -> str:
    result = omnimarket_bridge.run_local_review(
        dry_run=dry_run,
        max_iterations=max_iterations,
        required_clean_runs=required_clean_runs,
    )
    return json.dumps(result, indent=2, default=str)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
