"""
Multi-File Insights Aggregation (Phase C)

Provides cross-document analysis by:
1. Running Phase B summarization on each document
2. Extracting themes, overlaps, differences, entities
3. RAG-first with optional LLM synthesis
"""

from .aggregator_service import aggregate_insights
from .aggregator_tool import aggregate_insights_tool, get_insights_tool_definition

__all__ = [
    "aggregate_insights",
    "aggregate_insights_tool",
    "get_insights_tool_definition"
]
