"""
Document Summarizer Tool — Agent tool wrapper for document summarization.

Wraps existing summarizer service without duplicating logic.
"""

from typing import Dict, Any
from app.agents.tools.base_tool import AgentTool, ToolMetadata
from app.tools.summarizer.summarizer_service import summarize_document
from app.core.telemetry import ensure_complete_telemetry
from app.core.logging import setup_logger

logger = setup_logger("INFO")


class DocumentSummarizerTool(AgentTool):
    """
    Tool for summarizing documents.
    
    Wraps summarizer_service.summarize_document() with standardized interface.
    """
    
    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        return ToolMetadata(
            name="doc_summarizer",
            description="Summarize a document by document ID. Supports auto, extractive, and hybrid modes. Returns concise summary with key points and extractive mode always available without LLM.",
            inputs={
                "document_id": {
                    "type": "string",
                    "description": "Document ID to summarize",
                    "required": True
                },
                "mode": {
                    "type": "string",
                    "description": "Summarization mode: auto (default), extractive, or hybrid",
                    "required": False,
                    "default": "auto",
                    "enum": ["auto", "extractive", "hybrid"]
                },
                "max_chunks": {
                    "type": "integer",
                    "description": "Maximum chunks to retrieve (default 5)",
                    "required": False,
                    "default": 5
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "document_id": {"type": "string"},
                    "mode_used": {"type": "string"},
                    "chunks_used": {"type": "integer"},
                    "narrative_insight": {"type": "object"}
                }
            },
            uses_llm=True,  # Hybrid mode uses LLM, but extractive doesn't
            category="document_processing",
            supports_export=True,  # Summaries can be exported to md/pdf
            requires_document=True,  # Requires document to be in system
            supports_batch=False,  # One document at a time
            examples=[
                {
                    "input": {"document_id": "doc_123", "mode": "auto"},
                    "description": "Summarize document with automatic mode selection"
                },
                {
                    "input": {"document_id": "doc_456", "mode": "extractive", "max_chunks": 3},
                    "description": "Fast extractive summary without LLM"
                },
                {
                    "input": {"document_id": "doc_789", "mode": "hybrid", "max_chunks": 10},
                    "description": "High-quality hybrid summary with LLM enhancement"
                }
            ]
        )
    
    def execute(self, **kwargs) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Execute document summarization.
        
        Args:
            document_id: Document ID to summarize
            mode: Summarization mode (auto, extractive, hybrid)
            max_chunks: Maximum chunks to retrieve
            
        Returns:
            Tuple of (summary_result, telemetry)
        """
        document_id = kwargs.get("document_id")
        mode = kwargs.get("mode", "auto")
        max_chunks = kwargs.get("max_chunks", 5)
        
        logger.info(f"Tool execution: doc_summarizer - document_id={document_id}, mode={mode}")
        
        try:
            # Call existing service (no logic duplication)
            summary, telemetry = summarize_document(
                document_id=document_id,
                mode=mode,
                max_chunks=max_chunks
            )
            
            # Ensure telemetry is complete
            telemetry = ensure_complete_telemetry(telemetry)
            telemetry["routing_decision"] = f"doc_summarizer_{mode}"
            
            # Build result
            result = {
                "summary": summary,
                "document_id": document_id,
                "mode_used": telemetry.get("mode_used", mode),
                "chunks_used": telemetry.get("chunks_used", 0)
            }
            
            logger.info(f"Tool success: doc_summarizer - {len(summary)} chars, {result['chunks_used']} chunks")
            
            return result, telemetry
            
        except Exception as e:
            logger.error(f"Tool error: doc_summarizer - {str(e)}")
            
            # Return graceful error with complete telemetry
            telemetry = ensure_complete_telemetry({
                "routing_decision": "doc_summarizer_error",
                "fallback_triggered": True,
                "degradation_level": "failed",
                "graceful_message": f"Summarization failed: {str(e)}"
            })
            
            result = {
                "summary": f"Unable to summarize document {document_id}",
                "document_id": document_id,
                "error": str(e)
            }
            
            return result, telemetry


# Singleton instance
doc_summarizer_tool = DocumentSummarizerTool()
