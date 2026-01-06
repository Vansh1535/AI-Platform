"""
Cross-File Semantic Insights API

Provides semantic clustering and aggregation across multiple documents.
"""

from typing import Dict, Any, List, Optional
import time
from fastapi import HTTPException
from pydantic import BaseModel, Field
from app.core.logging import setup_logger

logger = setup_logger("INFO")


class CrossFileInsightRequest(BaseModel):
    """Request model for cross-file insights."""
    document_ids: List[str] = Field(..., description="List of document IDs to analyze")
    mode: str = Field(default="extractive", description="Analysis mode: extractive, semantic")
    enable_llm: bool = Field(default=False, description="Enable LLM-powered insights")


class SemanticCluster(BaseModel):
    """A semantic cluster of documents."""
    theme_label: str = Field(..., description="Descriptive label for the cluster theme")
    documents_involved: List[str] = Field(..., description="Document IDs in this cluster")
    evidence: List[Dict[str, Any]] = Field(..., description="Supporting evidence from documents")
    confidence_score: float = Field(..., description="Confidence in cluster quality (0-1)")


class CrossFileInsightResponse(BaseModel):
    """Response model for cross-file insights."""
    semantic_clusters: List[SemanticCluster] = Field(..., description="Identified semantic clusters")
    
    # Telemetry fields
    routing_decision: str = Field(..., description="How the request was routed")
    fallback_triggered: bool = Field(default=False, description="Whether fallback was used")
    degradation_level: str = Field(default="none", description="Degradation level")
    clustering_used: bool = Field(..., description="Whether clustering algorithms were used")
    cluster_count: int = Field(..., description="Number of clusters found")
    avg_cluster_confidence: float = Field(..., description="Average confidence across clusters")
    latency_ms_total: int = Field(..., description="Total processing time in milliseconds")
    graceful_message: Optional[str] = Field(default=None, description="Graceful degradation message")


async def generate_cross_file_insights(
    document_ids: List[str],
    mode: str = "extractive",
    enable_llm: bool = False
) -> CrossFileInsightResponse:
    """
    Generate semantic insights across multiple documents.
    
    Args:
        document_ids: List of document IDs to analyze
        mode: Analysis mode (extractive or semantic)
        enable_llm: Whether to enable LLM processing
        
    Returns:
        CrossFileInsightResponse with clusters and telemetry
    """
    start_time = time.time()
    
    # Initialize telemetry
    telemetry = {
        "routing_decision": "extractive_mode",
        "fallback_triggered": False,
        "degradation_level": "none",
        "clustering_used": False,
        "graceful_message": None
    }
    
    try:
        # Validate input
        if not document_ids:
            raise HTTPException(status_code=400, detail="No document IDs provided")
        
        if len(document_ids) < 2:
            # Single document - create a synthetic cluster
            clusters = [SemanticCluster(
                theme_label="Single Document Analysis",
                documents_involved=document_ids,
                evidence=[{
                    "doc_id": document_ids[0],
                    "preview": "Single document provided for cross-file analysis",
                    "similarity": 1.0
                }],
                confidence_score=0.8
            )]
            
            telemetry["degradation_level"] = "mild"
            telemetry["graceful_message"] = "Only one document provided - limited clustering available"
            telemetry["fallback_triggered"] = True
            
        else:
            # Multi-document analysis
            logger.info(f"Analyzing {len(document_ids)} documents for cross-file insights")
            
            # For now, implement extractive mode (semantic clustering would require vector analysis)
            if mode == "extractive":
                clusters = await _generate_extractive_clusters(document_ids)
                telemetry["routing_decision"] = "extractive_clusters"
            else:
                # Semantic mode - would require vector similarity analysis
                # For now, fall back to extractive with graceful message
                clusters = await _generate_extractive_clusters(document_ids)
                telemetry["routing_decision"] = "extractive_fallback"
                telemetry["fallback_triggered"] = True
                telemetry["degradation_level"] = "mild"
                telemetry["graceful_message"] = "Semantic clustering unavailable - using extractive mode"
        
        # Calculate cluster metrics
        cluster_count = len(clusters)
        avg_confidence = sum(c.confidence_score for c in clusters) / max(1, cluster_count)
        
        # Set clustering telemetry
        telemetry["clustering_used"] = cluster_count > 0
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        return CrossFileInsightResponse(
            semantic_clusters=clusters,
            routing_decision=telemetry["routing_decision"],
            fallback_triggered=telemetry["fallback_triggered"],
            degradation_level=telemetry["degradation_level"],
            clustering_used=telemetry["clustering_used"],
            cluster_count=cluster_count,
            avg_cluster_confidence=avg_confidence,
            latency_ms_total=latency_ms,
            graceful_message=telemetry["graceful_message"]
        )
        
    except Exception as e:
        logger.error(f"Cross-file insights failed: {str(e)}")
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Return graceful fallback
        return CrossFileInsightResponse(
            semantic_clusters=[],
            routing_decision="error_fallback",
            fallback_triggered=True,
            degradation_level="fallback",
            clustering_used=False,
            cluster_count=0,
            avg_cluster_confidence=0.0,
            latency_ms_total=latency_ms,
            graceful_message=f"Analysis failed: {str(e)} - returning empty result"
        )


async def _generate_extractive_clusters(document_ids: List[str]) -> List[SemanticCluster]:
    """
    Generate extractive clusters from documents.
    
    This is a simplified implementation that groups documents by basic metadata.
    In a full implementation, this would use vector similarity or NLP clustering.
    """
    from app.core.db.repository import DocumentRepository
    
    clusters = []
    
    try:
        # Get document metadata
        documents = []
        for doc_id in document_ids:
            doc = await DocumentRepository.get_document_by_id(doc_id)
            if doc:
                documents.append(doc)
        
        if not documents:
            return []
        
        # Simple clustering by file type
        type_groups = {}
        for doc in documents:
            # Determine file type from path or mime type
            file_type = "document"
            if doc.file_path:
                from pathlib import Path
                ext = Path(doc.file_path).suffix.lower()
                if ext in [".csv"]:
                    file_type = "data"
                elif ext in [".pdf", ".docx", ".doc", ".txt", ".md"]:
                    file_type = "text"
            
            if file_type not in type_groups:
                type_groups[file_type] = []
            type_groups[file_type].append(doc)
        
        # Create clusters from groups
        for file_type, docs in type_groups.items():
            cluster = SemanticCluster(
                theme_label=f"{file_type.title()} Files",
                documents_involved=[doc.id for doc in docs],
                evidence=[{
                    "doc_id": doc.id,
                    "preview": f"{doc.filename} ({doc.file_size} bytes)" if doc.file_size else doc.filename,
                    "similarity": 0.8  # Default similarity score
                } for doc in docs],
                confidence_score=0.7 if len(docs) > 1 else 0.5
            )
            clusters.append(cluster)
        
        return clusters
        
    except Exception as e:
        logger.warning(f"Extractive clustering failed: {str(e)} - returning empty clusters")
        return []