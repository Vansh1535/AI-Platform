"""
Summarizer tool definition for agent integration.
Allows agent to call document summarization functionality.
"""

from typing import Dict, Any, Tuple
from app.core.logging import setup_logger
from .summarizer_service import summarize_document

logger = setup_logger()


def summarize_document_tool(
    document_id: str = None,
    source: str = None,
    mode: str = "auto",
    max_chunks: int = 5,
    summary_length: str = "medium"
) -> Tuple[str, Dict[str, Any]]:
    """
    Agent-callable tool for document summarization.
    
    Args:
        document_id: Document ID to summarize (optional if source provided)
        source: Document source name (optional if document_id provided)
        mode: Summarization mode - auto/extractive/hybrid (default: auto)
        max_chunks: Maximum chunks to use (default: 5)
        summary_length: Summary length - short/medium/detailed (default: medium)
        
    Returns:
        Tuple of (summary_text, telemetry_dict)
        
    Raises:
        ValueError: If neither document_id nor source provided
    """
    # Validate arguments
    if not document_id and not source:
        raise ValueError("Either document_id or source must be provided")
    
    # Determine identifier to use
    if document_id:
        identifier = document_id
        logger.info(f"Summarizing document by ID: {document_id}")
    else:
        identifier = f"source:{source}"
        logger.info(f"Summarizing document by source: {source}")
    
    # Call summarization service
    try:
        summary, telemetry = summarize_document(
            document_id=identifier,
            mode=mode,
            max_chunks=max_chunks,
            summary_length=summary_length
        )
        
        logger.info(
            f"Summarization tool complete - "
            f"Mode: {telemetry.get('mode_used')}, "
            f"Chunks: {telemetry.get('chunks_used')}"
        )
        
        return summary, telemetry
        
    except Exception as e:
        logger.error(f"Summarization tool error: {str(e)}")
        
        # Return error with telemetry
        error_telemetry = {
            "routing": "summarizer_tool",
            "error_class": type(e).__name__,
            "mode_used": "error",
            "chunks_used": 0
        }
        
        return f"Failed to summarize: {str(e)}", error_telemetry


def get_summarizer_tool_definition() -> Dict[str, Any]:
    """
    Get tool definition for agent framework.
    
    Returns:
        Tool definition dictionary
    """
    return {
        "name": "summarize_document",
        "description": (
            "Generate a summary of a document using RAG-first extractive summarization "
            "with intelligent hybrid LLM fallback when confidence is low. "
            "Use this when the user asks for: summary, overview, explain document, "
            "what does this doc say, key points, main ideas. "
            "Returns structured summary with transparency metadata."
        ),
        "function": summarize_document_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Document ID to summarize (optional if source provided)"
                },
                "source": {
                    "type": "string",
                    "description": "Document source name (optional if document_id provided)"
                },
                "mode": {
                    "type": "string",
                    "enum": ["auto", "extractive", "hybrid"],
                    "description": "Summarization mode: auto (recommended), extractive (RAG-only), or hybrid (RAG+LLM)",
                    "default": "auto"
                },
                "max_chunks": {
                    "type": "integer",
                    "description": "Maximum chunks to retrieve (default: 5)",
                    "default": 5
                },
                "summary_length": {
                    "type": "string",
                    "enum": ["short", "medium", "detailed"],
                    "description": "Summary length: short (3 points), medium (5 points), detailed (8 points)",
                    "default": "medium"
                }
            },
            "required": []
        }
    }


# Tool registry entry
SUMMARIZER_TOOL = {
    "name": "summarize_document",
    "function": summarize_document_tool,
    "definition": get_summarizer_tool_definition()
}
