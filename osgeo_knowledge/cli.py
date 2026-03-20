"""CLI entry point for osgeo-knowledge."""

import argparse
import sys


def main():
    """Main CLI dispatcher."""
    parser = argparse.ArgumentParser(
        prog="osgeo-knowledge",
        description="OSGeo wiki knowledge base tools",
    )
    subparsers = parser.add_subparsers(dest="command")

    # MCP server subcommand
    subparsers.add_parser("mcp", help="Start the MCP server (STDIO transport)")

    args = parser.parse_args()

    if args.command == "mcp":
        from osgeo_knowledge.servers.mcp import main as mcp_main

        mcp_main()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
