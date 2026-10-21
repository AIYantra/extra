"""
Project Extra — Model Context Protocol (MCP) Server Package.
"""

__all__ = ["server", "main"]


def __getattr__(name: str):
    if name in ("server", "main"):
        from extra.mcp.server import main, server

        return server if name == "server" else main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
