"""
Summarizer tool package.
Provides document summarization using RAG-first extractive + hybrid LLM fallback.
"""

from .summarizer_service import summarize_document
from .summarizer_tool import summarize_document_tool, get_summarizer_tool_definition

__all__ = [
    "summarize_document",
    "summarize_document_tool",
    "get_summarizer_tool_definition"
]
