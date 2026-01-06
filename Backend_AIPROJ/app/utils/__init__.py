"""
Utility modules for the RAG system.
"""

from .graceful_response import (
    success_message,
    graceful_fallback,
    graceful_failure,
    DegradationLevel
)

__all__ = [
    "success_message",
    "graceful_fallback",
    "graceful_failure",
    "DegradationLevel"
]
