"""
Engram MCP - Persistent Memory for AI Assistants

Give your AI assistant a memory. Persistent, semantic, human-inspired.
"""

__version__ = "0.1.0"
__author__ = "Creator AI Studio"


def serve() -> None:
    """Run the Engram MCP server.

    This is called when you run: python -m engram.server
    Or when Claude Code starts Engram as an MCP server.
    """
    from engram.server import serve as _serve
    _serve()


__all__ = ["serve", "__version__"]
