#!/usr/bin/env python3
"""VisualSynapse CLI entry point."""

import argparse
import sys
import os


def main():
    parser = argparse.ArgumentParser(
        prog="synapse",
        description="VisualSynapse - Code Logic Visualization"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    serve_parser = subparsers.add_parser("serve", help="Start the web UI server")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port to run on")
    serve_parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")

    mcp_parser = subparsers.add_parser("mcp", help="Run as MCP server (stdio)")

    args = parser.parse_args()

    if args.command == "serve":
        from synapse.main import run_server
        run_server(host=args.host, port=args.port)
    elif args.command == "mcp":
        from synapse.main import run_mcp_stdio
        run_mcp_stdio()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
