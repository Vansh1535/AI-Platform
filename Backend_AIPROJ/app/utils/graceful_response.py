"""
Graceful Response Layer for RAG System

Provides human-friendly messaging for success, degradation, and failure cases
while maintaining full observability and metadata for debugging.

Design Principles:
- Never expose technical details to end users
- Never blame the user
- Always suggest a constructive next action
- Preserve all metadata for observability
- Keep messages short and clear (1-2 sentences max)
"""

from enum import Enum
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DegradationLevel(str, Enum):
    """
    Degradation levels for operations.
    
    - NONE: Operation succeeded fully
    - MILD: Operation succeeded with minor limitations
    - FALLBACK: Operation used fallback approach
    - DEGRADED: Operation succeeded partially with reduced quality
    - FAILED: Operation failed completely
    """
    NONE = "none"
    MILD = "mild"
    FALLBACK = "fallback"
    DEGRADED = "degraded"
    FAILED = "failed"


# Context-specific message templates
_MESSAGE_TEMPLATES = {
    # RAG Search/Ask
    "rag_no_results": "I couldn't find information about this in the documents.",
    "rag_low_confidence": "I couldn't find a confident answer in the documents.",
    "rag_no_documents": "No documents are available to search.",
    "rag_retrieval_error": "I encountered an issue searching the documents.",
    
    # Summarization
    "summarize_too_short": "The document is too small to summarize meaningfully.",
    "summarize_no_content": "The document doesn't contain enough content to summarize.",
    "summarize_low_quality": "The summary has low confidence due to limited content quality.",
    "summarize_extractive_fallback": "Generated a basic summary using key sentences.",
    
    # Insights/Aggregation
    "insights_too_few_docs": "At least 2 documents are needed for cross-document insights.",
    "insights_no_clustering": "Insights were generated without semantic grouping due to low signal.",
    "insights_partial_failure": "Some documents couldn't be processed, but insights were generated from available documents.",
    "insights_all_failed": "None of the documents could be processed successfully.",
    
    # CSV/Structured Data
    "csv_insufficient_data": "This dataset doesn't contain enough structured information for analysis.",
    "csv_no_variance": "This dataset lacks enough variation for meaningful insights.",
    "csv_format_error": "The data format isn't suitable for analysis.",
    
    # Generic
    "generic_fallback": "The operation completed with limitations.",
    "generic_error": "An unexpected issue occurred during processing."
}


# Context-specific user action hints
_ACTION_HINTS = {
    # RAG
    "rag_no_results": "Try rephrasing your question or using different keywords.",
    "rag_low_confidence": "Try rephrasing the question or upload a document with more details.",
    "rag_no_documents": "Upload documents first to enable search.",
    "rag_retrieval_error": "Please try again or contact support if the issue persists.",
    
    # Summarization
    "summarize_too_short": "Upload a longer document for better summarization.",
    "summarize_no_content": "Ensure the document contains meaningful text content.",
    "summarize_low_quality": "Upload documents with richer content for better summaries.",
    "summarize_extractive_fallback": "The summary focuses on key sentences from the document.",
    
    # Insights
    "insights_too_few_docs": "Upload at least 2 documents to enable cross-document analysis.",
    "insights_no_clustering": "This doesn't affect the core insights—themes and overlaps are still available.",
    "insights_partial_failure": "Review the insights from successfully processed documents.",
    "insights_all_failed": "Check document IDs and try again with valid documents.",
    
    # CSV
    "csv_insufficient_data": "Try uploading a dataset with more rows or columns.",
    "csv_no_variance": "Ensure the data contains varied values for analysis.",
    "csv_format_error": "Check that the file is properly formatted as CSV.",
    
    # Generic
    "generic_fallback": "Results may be limited—consider refining your input.",
    "generic_error": "Please try again or contact support if the issue persists."
}


def success_message(
    context: str,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate a success message with full quality.
    
    Args:
        context: The operation context (e.g., "rag_search", "summarize")
        details: Optional additional details to include
        
    Returns:
        Dict with graceful_message, degradation_level, and user_action_hint
        
    Example:
        >>> success_message("rag_search", {"results": 5})
        {
            "graceful_message": None,
            "degradation_level": "none",
            "user_action_hint": None
        }
    """
    return {
        "graceful_message": None,  # No message needed for full success
        "degradation_level": DegradationLevel.NONE.value,
        "user_action_hint": None,
        **(details or {})
    }


def graceful_fallback(
    context: str,
    reason: str,
    suggestion: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate a graceful fallback message for degraded operations.
    
    Args:
        context: The operation context (e.g., "rag_low_confidence")
        reason: Internal reason for fallback (for logging/metadata)
        suggestion: Optional custom user action hint
        meta: Optional metadata to include
        
    Returns:
        Dict with graceful_message, degradation_level, user_action_hint, and metadata
        
    Example:
        >>> graceful_fallback("rag_low_confidence", "max_similarity=0.45")
        {
            "graceful_message": "I couldn't find a confident answer in the documents.",
            "degradation_level": "fallback",
            "user_action_hint": "Try rephrasing the question or upload a document with more details.",
            "fallback_reason": "max_similarity=0.45"
        }
    """
    # Get message template
    message = _MESSAGE_TEMPLATES.get(context, _MESSAGE_TEMPLATES["generic_fallback"])
    
    # Get action hint
    action_hint = suggestion or _ACTION_HINTS.get(context, _ACTION_HINTS["generic_fallback"])
    
    # Log fallback for observability
    logger.info(f"graceful_fallback context={context} reason={reason}")
    
    result = {
        "graceful_message": message,
        "degradation_level": DegradationLevel.FALLBACK.value,
        "user_action_hint": action_hint,
        "fallback_reason": reason
    }
    
    # Add any additional metadata
    if meta:
        result.update(meta)
    
    return result


def graceful_failure(
    context: str,
    error: str,
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate a graceful failure message for failed operations.
    
    Args:
        context: The operation context (e.g., "rag_retrieval_error")
        error: Internal error details (for logging/metadata only, not exposed to user)
        meta: Optional metadata to include
        
    Returns:
        Dict with graceful_message, degradation_level, user_action_hint, and error metadata
        
    Example:
        >>> graceful_failure("rag_retrieval_error", "ChromaDB connection timeout")
        {
            "graceful_message": "I encountered an issue searching the documents.",
            "degradation_level": "failed",
            "user_action_hint": "Please try again or contact support if the issue persists.",
            "error_type": "retrieval_error"
        }
    """
    # Get message template
    message = _MESSAGE_TEMPLATES.get(context, _MESSAGE_TEMPLATES["generic_error"])
    
    # Get action hint
    action_hint = _ACTION_HINTS.get(context, _ACTION_HINTS["generic_error"])
    
    # Log error for observability (with full error details)
    logger.error(f"graceful_failure context={context} error={error}")
    
    result = {
        "graceful_message": message,
        "degradation_level": DegradationLevel.FAILED.value,
        "user_action_hint": action_hint,
        "error_type": context.replace("_error", "").replace("_", " ")
    }
    
    # Add metadata (but NOT the raw error message to user)
    if meta:
        result.update(meta)
    
    return result


def add_graceful_context(
    response: Dict[str, Any],
    graceful_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Helper to merge graceful messaging into existing response dict.
    
    Args:
        response: Existing response dict
        graceful_data: Result from success_message/graceful_fallback/graceful_failure
        
    Returns:
        Merged response with graceful fields added
        
    Example:
        >>> response = {"answer": "Machine learning is...", "confidence": 0.85}
        >>> graceful = success_message("rag_search")
        >>> add_graceful_context(response, graceful)
        {
            "answer": "Machine learning is...",
            "confidence": 0.85,
            "graceful_message": None,
            "degradation_level": "none",
            "user_action_hint": None
        }
    """
    return {**response, **graceful_data}
