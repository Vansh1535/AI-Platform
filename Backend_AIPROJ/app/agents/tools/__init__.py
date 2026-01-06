"""
Agent Tools — Wrap stable platform capabilities as reusable agent tools.

Tools:
- doc_summarizer_tool: Summarize documents
- rag_answer_tool: Answer questions using RAG
- csv_insights_tool: Generate CSV insights
- cross_file_insight_tool: Analyze across multiple files

All tools:
- Accept structured arguments
- Call existing service layer (no duplication)
- Return consistent telemetry + graceful messages
- Never bypass safety or fallback logic
- Expose metadata (name, description, inputs, outputs, uses_llm)
"""

from .base_tool import AgentTool, ToolMetadata
from .doc_summarizer_tool import doc_summarizer_tool
from .rag_answer_tool import rag_answer_tool
from .csv_insights_tool import csv_insights_tool
from .cross_file_insight_tool import cross_file_insight_tool

# Registry of all available tools
AGENT_TOOLS = {
    "doc_summarizer": doc_summarizer_tool,
    "rag_answer": rag_answer_tool,
    "csv_insights": csv_insights_tool,
    "cross_file_insight": cross_file_insight_tool
}

__all__ = [
    "AgentTool",
    "ToolMetadata",
    "doc_summarizer_tool",
    "rag_answer_tool",
    "csv_insights_tool",
    "cross_file_insight_tool",
    "AGENT_TOOLS"
]
