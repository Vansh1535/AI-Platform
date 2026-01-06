"""
RAG Answer Tool — Agent tool wrapper for RAG question answering.

Wraps existing RAG answer service without duplicating logic.
"""

from typing import Dict, Any
from app.agents.tools.base_tool import AgentTool, ToolMetadata
from app.rag.qa.answer import generate_answer
from app.core.telemetry import ensure_complete_telemetry
from app.core.logging import setup_logger

logger = setup_logger("INFO")


class RAGAnswerTool(AgentTool):
    """
    Tool for answering questions using RAG.
    
    Wraps rag.qa.answer.generate_answer() with standardized interface.
    """
    
    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        return ToolMetadata(
            name="rag_answer",
            description="Answer a question using Retrieval-Augmented Generation (RAG). Retrieves relevant document chunks and generates answer with citations. Supports safe modes and confidence thresholds. Output includes citations and confidence scores for reliable answers.",
            inputs={
                "question": {
                    "type": "string",
                    "description": "Question to answer",
                    "required": True
                },
                "document_id": {
                    "type": "string",
                    "description": "Optional document ID to filter retrieval",
                    "required": False
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of chunks to retrieve (default 5)",
                    "required": False,
                    "default": 5
                },
                "safe_mode": {
                    "type": "string",
                    "description": "Safe mode: strict (extractive only) or hybrid (fallback to LLM)",
                    "required": False,
                    "enum": ["strict", "hybrid"]
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "answer": {"type": "string"},
                    "citations": {"type": "array"},
                    "used_chunks": {"type": "integer"},
                    "confidence": {"type": "number"},
                    "narrative_insight": {"type": "object"}
                }
            },
            uses_llm=True,
            category="question_answering",
            supports_export=True,  # Can export answers to md/pdf
            requires_document=False,  # Works with knowledge base
            supports_batch=False,  # One question at a time
            examples=[
                {
                    "input": {"question": "What is machine learning?", "top_k": 5},
                    "description": "Answer general question using RAG"
                },
                {
                    "input": {"question": "Specific detail?", "document_id": "doc_123", "safe_mode": "strict"},
                    "description": "Answer restricted to specific document with extractive mode"
                }
            ]
        )
    
    def execute(self, **kwargs) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Execute RAG question answering.
        
        Args:
            question: Question to answer
            document_id: Optional document filter
            top_k: Number of chunks to retrieve
            safe_mode: Safe mode (strict or hybrid)
            
        Returns:
            Tuple of (answer_result, telemetry)
        """
        question = kwargs.get("question")
        document_id = kwargs.get("document_id")
        top_k = kwargs.get("top_k", 5)
        safe_mode = kwargs.get("safe_mode")
        
        logger.info(f"Tool execution: rag_answer - question='{question[:50]}...', top_k={top_k}")
        
        try:
            # Build kwargs for generate_answer
            answer_kwargs = {
                "question": question,
                "top_k": top_k
            }
            if document_id:
                answer_kwargs["document_id"] = document_id
            if safe_mode:
                answer_kwargs["safe_mode"] = safe_mode
            
            # Call existing service (no logic duplication)
            result, telemetry = generate_answer(**answer_kwargs)
            
            # Ensure telemetry is complete
            telemetry = ensure_complete_telemetry(telemetry)
            telemetry["routing_decision"] = "rag_answer"
            
            # Add confidence if not present
            if "confidence" not in result:
                result["confidence"] = telemetry.get("confidence_score", 0.0)
            
            logger.info(
                f"Tool success: rag_answer - answer_length={len(result.get('answer', ''))}, "
                f"citations={result.get('used_chunks', 0)}"
            )
            
            return result, telemetry
            
        except Exception as e:
            logger.error(f"Tool error: rag_answer - {str(e)}")
            
            # Return graceful error with complete telemetry
            telemetry = ensure_complete_telemetry({
                "routing_decision": "rag_answer_error",
                "fallback_triggered": True,
                "degradation_level": "failed",
                "graceful_message": f"Answer generation failed: {str(e)}"
            })
            
            result = {
                "answer": "Unable to generate answer due to an error",
                "citations": [],
                "used_chunks": 0,
                "error": str(e)
            }
            
            return result, telemetry


# Singleton instance
rag_answer_tool = RAGAnswerTool()
