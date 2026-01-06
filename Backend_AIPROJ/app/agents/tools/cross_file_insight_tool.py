"""
Cross-File Insight Tool — Agent tool wrapper for cross-file analysis.

Wraps existing cross-file aggregation service without duplicating logic.
"""

from typing import Dict, Any, List
from app.agents.tools.base_tool import AgentTool, ToolMetadata
from app.tools.insights.aggregator_service import aggregate_insights
from app.core.telemetry import ensure_complete_telemetry
from app.core.logging import setup_logger

logger = setup_logger("INFO")


class CrossFileInsightTool(AgentTool):
    """
    Tool for cross-file insight aggregation.
    
    Wraps insights.aggregator_service.aggregate_insights() with standardized interface.
    """
    
    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        return ToolMetadata(
            name="cross_file_insight",
            description="Analyze multiple documents to extract cross-file insights, common themes, overlaps, and relationships. Requires at least 2 documents. Supports extractive (deterministic) and hybrid (LLM-enhanced) modes. Returns aggregated themes, per-document summaries, and optional semantic clusters.",
            inputs={
                "document_ids": {
                    "type": "array",
                    "description": "List of document IDs to analyze (minimum 2)",
                    "required": True,
                    "items": {"type": "string"},
                    "minItems": 2
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
                    "description": "Maximum chunks per document (default 5)",
                    "required": False,
                    "default": 5
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "per_document": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "document_id": {"type": "string"},
                                "summary": {"type": "string"},
                                "confidence": {"type": "number"}
                            }
                        }
                    },
                    "aggregated_insights": {
                        "type": "object",
                        "properties": {
                            "themes": {"type": "array"},
                            "overlaps": {"type": "array"},
                            "semantic_clusters": {"type": "array"}
                        }
                    },
                    "narrative_insight": {"type": "object"}
                }
            },
            uses_llm=True,  # Hybrid mode uses LLM
            category="multi_document_analysis",
            supports_export=True,  # Aggregated insights can be exported
            requires_document=True,  # Requires documents in system
            supports_batch=True,  # Processes multiple documents together
            examples=[
                {
                    "input": {
                        "document_ids": ["doc_1", "doc_2", "doc_3"],
                        "mode": "auto"
                    },
                    "description": "Analyze common themes across 3 documents"
                },
                {
                    "input": {
                        "document_ids": ["doc_report1", "doc_report2"],
                        "mode": "extractive",
                        "max_chunks": 3
                    },
                    "description": "Fast extractive cross-file analysis without LLM"
                },
                {
                    "input": {
                        "document_ids": ["doc_a", "doc_b", "doc_c", "doc_d"],
                        "mode": "hybrid",
                        "max_chunks": 10
                    },
                    "description": "In-depth hybrid analysis with LLM-powered theme synthesis"
                }
            ]
        )
    
    def execute(self, **kwargs) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Execute cross-file insight aggregation.
        
        Args:
            document_ids: List of document IDs to analyze
            mode: Summarization mode (auto, extractive, hybrid)
            max_chunks: Maximum chunks per document
            
        Returns:
            Tuple of (aggregated_insights, telemetry)
        """
        document_ids = kwargs.get("document_ids", [])
        mode = kwargs.get("mode", "auto")
        max_chunks = kwargs.get("max_chunks", 5)
        
        # Validate minimum documents
        if len(document_ids) < 2:
            logger.error("Tool error: cross_file_insight - requires at least 2 documents")
            telemetry = ensure_complete_telemetry({
                "routing_decision": "cross_file_insight_error",
                "fallback_triggered": True,
                "degradation_level": "failed",
                "graceful_message": "Cross-file analysis requires at least 2 documents"
            })
            return {
                "error": "Minimum 2 documents required",
                "per_document": [],
                "aggregated_insights": {}
            }, telemetry
        
        logger.info(
            f"Tool execution: cross_file_insight - "
            f"documents={len(document_ids)}, mode={mode}"
        )
        
        try:
            # Call existing service (no logic duplication)
            result, telemetry = aggregate_insights(
                document_ids=document_ids,
                mode=mode,
                max_chunks=max_chunks
            )
            
            # Ensure telemetry is complete
            telemetry = ensure_complete_telemetry(telemetry)
            telemetry["routing_decision"] = f"cross_file_insight_{mode}"
            
            logger.info(
                f"Tool success: cross_file_insight - "
                f"processed={telemetry.get('files_processed', 0)}, "
                f"failed={telemetry.get('files_failed', 0)}, "
                f"themes={len(result.get('aggregated_insights', {}).get('themes', []))}"
            )
            
            return result, telemetry
            
        except ValueError as e:
            # Handle validation errors (e.g., too few documents)
            logger.error(f"Tool validation error: cross_file_insight - {str(e)}")
            
            telemetry = ensure_complete_telemetry({
                "routing_decision": "cross_file_insight_validation_error",
                "fallback_triggered": True,
                "degradation_level": "failed",
                "graceful_message": str(e)
            })
            
            result = {
                "error": str(e),
                "per_document": [],
                "aggregated_insights": {}
            }
            
            return result, telemetry
            
        except Exception as e:
            logger.error(f"Tool error: cross_file_insight - {str(e)}")
            
            # Return graceful error with complete telemetry
            telemetry = ensure_complete_telemetry({
                "routing_decision": "cross_file_insight_error",
                "fallback_triggered": True,
                "degradation_level": "failed",
                "graceful_message": f"Cross-file analysis failed: {str(e)}"
            })
            
            result = {
                "error": str(e),
                "per_document": [],
                "aggregated_insights": {
                    "themes": [],
                    "overlaps": []
                }
            }
            
            return result, telemetry


# Singleton instance
cross_file_insight_tool = CrossFileInsightTool()
