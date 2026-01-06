"""
Multi-file ingestion module with dispatcher pattern.
Supports: PDF, TXT, MD, DOCX, CSV
"""

from .dispatcher import dispatch_file, ParsedDocument
from .normalize import normalize_content

__all__ = [
    "dispatch_file",
    "ParsedDocument",
    "normalize_content"
]
