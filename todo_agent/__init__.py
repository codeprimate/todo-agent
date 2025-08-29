"""
Todo Agent - A natural language interface for todo.sh task management.
"""

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

__author__ = "codeprimate"

from .main import main

__all__ = ["main"]
