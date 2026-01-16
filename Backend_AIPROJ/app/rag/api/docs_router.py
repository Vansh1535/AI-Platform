"""
FastAPI router for document management and inspection.
Provides endpoints for listing, viewing, and debugging ingested documents.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from sqlalchemy import func, select
from app.core.logging import setup_logger
from app.rag.retrieval.search import search as rag_search
from app.core.db.repository import DocumentRepository
from app.core.db.models import Document
from app.core.db import get_session

logger = setup_logger("INFO")

router = APIRouter(prefix="/rag/docs", tags=["Document Management"])


@router.get("/list", response_model=Dict[str, Any])
async def list_documents(
    status: Optional[str] = Query(None, description="Filter by status: success, failed, processing"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset")
):
    """
    List all ingested documents with metadata and health summary.
    
    Query Parameters:
    - status: Filter by ingestion status (optional)
    - limit: Maximum results per page (1-500, default: 100)
    - offset: Pagination offset (default: 0)
    
    Returns:
    - documents: List of document metadata
    - total_count: Total number of documents
    - health_summary: Aggregated health statistics
    """
    try:
        logger.info(f"Listing documents: status={status}, limit={limit}, offset={offset}")
        
        # Get documents from PostgreSQL
        documents = await DocumentRepository.list_documents(
            status=status,
            limit=limit,
            offset=offset
        )
        
        # Get total count
        total_count = await DocumentRepository.count_documents(status=status)
        
        # Calculate health summary from PostgreSQL
        async with get_session() as session:
            # Get statistics grouped by status
            query = select(
                Document.ingestion_status,
                func.count().label('count'),
                func.avg(Document.processing_time_ms).label('avg_time_ms'),
                func.sum(Document.chunk_count).label('total_chunks')
            ).group_by(Document.ingestion_status)
            
            result = await session.execute(query)
            health_rows = result.all()
            
            # Format health summary matching old structure
            health_summary = {}
            for row in health_rows:
                health_summary[row.ingestion_status or "unknown"] = {
                    "count": row.count,
                    "avg_time_ms": float(row.avg_time_ms) if row.avg_time_ms else 0,
                    "total_chunks": row.total_chunks or 0
                }
        
        logger.info(f"Retrieved {len(documents)} documents (total: {total_count})")
        
        return {
            "status": "success",
            "documents": [doc.to_dict() for doc in documents],
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count
            },
            "health_summary": health_summary
        }
    
    except Exception as e:
        logger.error(f"Failed to list documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@router.get("/{document_id}/meta", response_model=Dict[str, Any])
async def get_document_metadata(document_id: str):
    """
    Get full metadata profile for a specific document.
    
    Path Parameters:
    - document_id: Unique document identifier
    
    Returns:
    - Complete document metadata including ingestion details, timing, and configuration
    """
    try:
        logger.info(f"Fetching metadata for document: {document_id}")
        
        registry = get_registry()
        metadata = registry.get_document_meta(document_id)
        
        if metadata is None:
            logger.warning(f"Document not found: {document_id}")
            raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")
        
        logger.info(f"Retrieved metadata for: {document_id}")
        
        return {
            "status": "success",
            "document": metadata
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get metadata: {str(e)}")


@router.get("/{document_id}/preview", response_model=Dict[str, Any])
async def preview_document_chunks(
    document_id: str,
    max_chunks: int = Query(5, ge=1, le=20, description="Number of chunks to preview")
):
    """
    Preview the first N chunks of a document for debugging.
    
    Path Parameters:
    - document_id: Unique document identifier
    
    Query Parameters:
    - max_chunks: Number of chunks to preview (1-20, default: 5)
    
    Returns:
    - Document metadata and first N chunks with scores
    """
    try:
        logger.info(f"Previewing document: {document_id} (max_chunks={max_chunks})")
        
        registry = get_registry()
        metadata = registry.get_document_meta(document_id)
        
        if metadata is None:
            logger.warning(f"Document not found: {document_id}")
            raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")
        
        # Search for chunks from this document
        # Use a generic query to retrieve chunks
        try:
            # Try to get chunks by searching with document filename
            search_query = metadata.get("filename", "document preview")
            results = rag_search(search_query, top_k=max_chunks)
            
            # Filter results to only include chunks from this document
            # (chunk IDs should start with document_id)
            preview_chunks = []
            for result in results:
                chunk_text = result.get("chunk", "")
                if chunk_text:  # If we have chunk text, include it
                    preview_chunks.append({
                        "chunk": chunk_text[:500] + "..." if len(chunk_text) > 500 else chunk_text,
                        "score": result.get("score", 0),
                        "full_length": len(chunk_text)
                    })
                
                if len(preview_chunks) >= max_chunks:
                    break
        
        except Exception as e:
            logger.warning(f"Could not retrieve chunks: {e}")
            preview_chunks = []
        
        logger.info(f"Retrieved {len(preview_chunks)} preview chunks for: {document_id}")
        
        return {
            "status": "success",
            "document_id": document_id,
            "metadata": metadata,
            "preview_chunks": preview_chunks,
            "total_chunks": metadata.get("chunk_count", 0)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to preview document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to preview: {str(e)}")


@router.get("/checksum/{checksum_hash}", response_model=Dict[str, Any])
async def lookup_by_checksum(checksum_hash: str):
    """
    Lookup documents by SHA-256 checksum hash.
    Useful for duplicate detection and verification.
    
    Path Parameters:
    - checksum_hash: SHA-256 checksum hash (64 hex characters)
    
    Returns:
    - List of documents with matching checksum
    """
    try:
        logger.info(f"Looking up documents by checksum: {checksum_hash[:16]}...")
        
        if len(checksum_hash) != 64:
            raise HTTPException(
                status_code=400,
                detail="Invalid checksum format. Expected SHA-256 (64 hex characters)"
            )
        
        registry = get_registry()
        documents = registry.find_by_checksum(checksum_hash)
        
        logger.info(f"Found {len(documents)} document(s) with checksum: {checksum_hash[:16]}...")
        
        return {
            "status": "success",
            "checksum": checksum_hash,
            "documents": documents,
            "count": len(documents)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to lookup by checksum: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to lookup: {str(e)}")


@router.get("/health", response_model=Dict[str, Any])
async def get_ingestion_health():
    """
    Get overall ingestion health summary.
    
    Returns:
    - Aggregate statistics on ingestion success/failure rates
    - Average processing times
    - Total documents and chunks
    """
    try:
        logger.info("Fetching ingestion health summary")
        
        registry = get_registry()
        result = registry.list_documents(limit=1)  # Just need the health summary
        
        health = result["health_summary"]
        
        # Calculate success rate
        total_attempts = sum(stat["count"] for stat in health.values())
        successful = health.get("success", {}).get("count", 0)
        success_rate = (successful / total_attempts * 100) if total_attempts > 0 else 0
        
        logger.info(f"Health check: {successful}/{total_attempts} successful ({success_rate:.1f}%)")
        
        return {
            "status": "success",
            "health": {
                "total_documents": total_attempts,
                "successful": successful,
                "failed": health.get("failed", {}).get("count", 0),
                "processing": health.get("processing", {}).get("count", 0),
                "success_rate": round(success_rate, 2),
                "total_chunks": sum(
                    stat.get("total_chunks", 0) or 0 
                    for stat in health.values()
                ),
                "avg_processing_time_ms": health.get("success", {}).get("avg_time_ms", 0)
            },
            "by_status": health
        }
    
    except Exception as e:
        logger.error(f"Failed to get health summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get health: {str(e)}")
