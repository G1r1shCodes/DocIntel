"""
Backward-compatibility shim.

``from parsers.base_parser import DocumentData, PageData`` still works
but the canonical home is now ``parsers.base``.
"""

from .base import DocumentData, PageData  # noqa: F401
