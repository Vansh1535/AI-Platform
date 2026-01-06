"""
Document Service — PostgreSQL-backed document registry replacement

Replaces SQLite-based DocumentRegistry with async PostgreSQL operations.
Maintains full API compatibility with existing ingestion pipeline.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import time

from app.core.db import (
    DocumentRepository,
    IngestionEventRepository,
    ChunkRepository,
    check_database_connection,
)
from app.core.db.graceful import (
    graceful_db_operation,
    safe_db_call,
    create_degraded_response,
    GracefulDatabaseContext
)
from app.core.logging import setup_logger

logger = setup_logger("INFO")


class DocumentService:
    """
    Document service providing registry operations backed by PostgreSQL.
    
    Drop-in replacement for SQLite DocumentRegistry with identical API.
    All methods are async and include graceful degradation if DB unavailable.
    """
    
    def __init__(self):
        """Initialize document service."""
        self.db_available = False
        self._check_availability()
    
    def _check_availability(self):
        """Check if database is available (sync check for compatibility)."""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in async context, can't check now
                self.db_available = True  # Optimistic
            else:
                self.db_available, error = loop.run_until_complete(check_database_connection())
                if not self.db_available:
                    logger.warning(f"Database unavailable: {error}")
        except Exception as e:
            logger.warning(f"Could not check database availability: {e}")
            self.db_available = False
    
    @graceful_db_operation(
        fallback_value={"status": "degraded", "document_id": None},
        operation_name="register ingestion start"
    )
    async def register_ingestion_start(
        self,
        document_id: str,
        filename: str,
        file_type: str,
        file_size_bytes: int,
        checksum_hash: str,
        source_path: str,
        chunk_size: int = 200,
        overlap: int = 50,
        tokenizer_name: str = "character",
        exists_policy: str = "skip"
    ) -> Dict[str, Any]:
        """
        Register the start of document ingestion.
        
        Compatible with DocumentRegistry.register_ingestion_start()
        
        Args:
            document_id: Unique document identifier
            filename: Original filename
            file_type: File type (pdf, txt, md, etc.)
            file_size_bytes: File size in bytes
            checksum_hash: SHA-256 checksum
            source_path: Source file path
            chunk_size: Chunking configuration
            overlap: Chunk overlap size
            tokenizer_name: Tokenizer used
            exists_policy: Policy for existing documents
            
        Returns:
            dict: Registration metadata
        """
        try:
            # Determine MIME type from file_type
            mime_map = {
                "pdf": "application/pdf",
                "txt": "text/plain",
                "md": "text/markdown",
                "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "csv": "text/csv"
            }
            mime_type = mime_map.get(file_type.lower(), "application/octet-stream")
            
            # Check if document already exists (for overwrite policy)
            existing_document = await DocumentRepository.get_document_by_id(document_id)
            
            if existing_document:
                # Update existing document for overwrite
                logger.info(f"Updating existing document: {document_id}")
                document = await DocumentRepository.update_document(
                    document_id=document_id,
                    filename=filename,
                    file_hash=checksum_hash,
                    file_size=file_size_bytes,
                    file_path=source_path,
                    mime_type=mime_type,
                    ingestion_status="processing",
                    ingestion_version="1",
                    document_metadata={
                        "file_type": file_type,
                        "chunk_size": chunk_size,
                        "overlap": overlap,
                        "tokenizer_name": tokenizer_name,
                        "exists_policy": exists_policy
                    }
                )
            else:
                # Create new document
                document = await DocumentRepository.create_document(
                    document_id=document_id,
                    filename=filename,
                    file_hash=checksum_hash,
                    file_size=file_size_bytes,
                    file_path=source_path,
                    mime_type=mime_type,
                    ingestion_status="processing",
                    ingestion_version="1",
                    document_metadata={
                        "file_type": file_type,
                        "chunk_size": chunk_size,
                        "overlap": overlap,
                        "tokenizer_name": tokenizer_name,
                        "exists_policy": exists_policy
                    }
                )
            
            # Create ingestion event
            await IngestionEventRepository.create_event(
                document_id=document_id,
                event_type="ingestion_started",
                event_status="success",
                ingestion_mode="standard",
                triggered_by="api"
            )
            
            logger.info(f"✅ Registered ingestion start: {document_id} ({filename})")
            
            return {
                "document_id": document_id,
                "status": "processing",
                "created_at": document.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to register ingestion start: {str(e)}")
            return {
                "error": str(e),
                "document_id": document_id,
                "graceful_message": "Registry unavailable - ingestion will continue without persistence"
            }
    
    @graceful_db_operation(
        fallback_value={"status": "degraded", "document_id": None},
        operation_name="register ingestion success"
    )
    async def register_ingestion_success(
        self,
        document_id: str,
        page_count: int,
        chunk_count: int,
        token_estimate: int,
        processing_time_ms: int
    ) -> Dict[str, Any]:
        """
        Register successful completion of document ingestion.
        
        Compatible with DocumentRegistry.register_ingestion_success()
        
        Args:
            document_id: Document identifier
            page_count: Number of pages processed
            chunk_count: Number of chunks created
            token_estimate: Estimated token count
            processing_time_ms: Processing time in milliseconds
            
        Returns:
            dict: Success metadata
        """
        try:
            # Update document status
            document = await DocumentRepository.update_document(
                document_id=document_id,
                ingestion_status="completed",
                chunk_count=chunk_count,
                processing_time_ms=processing_time_ms,
                ingestion_timestamp=datetime.utcnow(),
                document_metadata={
                    "page_count": page_count,
                    "token_estimate": token_estimate
                }
            )
            
            if not document:
                logger.warning(f"Document not found for success update: {document_id}")
                return {"error": "Document not found", "document_id": document_id}
            
            # Create success event
            await IngestionEventRepository.create_event(
                document_id=document_id,
                event_type="ingestion_completed",
                event_status="success",
                processing_time_ms=processing_time_ms,
                chunks_created=chunk_count,
                telemetry={
                    "page_count": page_count,
                    "token_estimate": token_estimate
                }
            )
            
            logger.info(f"✅ Registered ingestion success: {document_id} ({chunk_count} chunks)")
            
            return {
                "document_id": document_id,
                "status": "completed",
                "chunk_count": chunk_count,
                "updated_at": document.updated_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to register ingestion success: {str(e)}")
            return {
                "error": str(e),
                "document_id": document_id,
                "graceful_message": "Could not update registry - document ingested but not tracked"
            }
    
    @graceful_db_operation(
        fallback_value={"status": "degraded", "document_id": None},
        operation_name="register ingestion failure"
    )
    async def register_ingestion_failure(
        self,
        document_id: str,
        failure_reason: str,
        processing_time_ms: int
    ) -> Dict[str, Any]:
        """
        Register failed document ingestion.
        
        Compatible with DocumentRegistry.register_ingestion_failure()
        
        Args:
            document_id: Document identifier
            failure_reason: Reason for failure
            processing_time_ms: Processing time before failure
            
        Returns:
            dict: Failure metadata
        """
        try:
            # Update document status
            document = await DocumentRepository.update_document(
                document_id=document_id,
                ingestion_status="failed",
                processing_time_ms=processing_time_ms,
                graceful_message=failure_reason,
                degradation_level="error"
            )
            
            if not document:
                logger.warning(f"Document not found for failure update: {document_id}")
                return {"error": "Document not found", "document_id": document_id}
            
            # Create failure event
            await IngestionEventRepository.create_event(
                document_id=document_id,
                event_type="ingestion_failed",
                event_status="failure",
                processing_time_ms=processing_time_ms,
                error_message=failure_reason,
                error_type="ingestion_error"
            )
            
            logger.error(f"❌ Registered ingestion failure: {document_id} - {failure_reason}")
            
            return {
                "document_id": document_id,
                "status": "failed",
                "failure_reason": failure_reason,
                "updated_at": document.updated_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to register ingestion failure: {str(e)}")
            return {
                "error": str(e),
                "document_id": document_id
            }
    
    @graceful_db_operation(
        fallback_value=None,
        operation_name="get document by checksum"
    )
    async def get_document_by_checksum(self, checksum: str) -> Optional[Dict[str, Any]]:
        """
        Find document by checksum (for duplicate detection).
        With graceful degradation - returns None if DB unavailable.
        
        Args:
            checksum: SHA-256 file checksum
            
        Returns:
            Document dict or None if not found or DB unavailable
        """
        document = await DocumentRepository.get_document_by_hash(checksum)
        
        if document:
            return document.to_dict()
        
        return None
    
    @graceful_db_operation(
        fallback_value=[],
        operation_name="list documents by status"
    )
    async def list_documents_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        List documents filtered by ingestion status.
        With graceful degradation - returns empty list if DB unavailable.
        
        Args:
            status: Filter by status (processing, completed, failed)
            
        Returns:
            List of document dicts (empty if DB unavailable)
        """
        documents = await DocumentRepository.list_documents(status=status, limit=1000)
        return [doc.to_dict() for doc in documents]
    
    @graceful_db_operation(
        fallback_value=None,
        operation_name="get document by ID"
    )
    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document by ID.
        With graceful degradation - returns None if DB unavailable.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Document dict or None if not found or DB unavailable
        """
        document = await DocumentRepository.get_document_by_id(document_id)
        
        if document:
            return document.to_dict()
        
        return None
    
    @graceful_db_operation(
        fallback_value=[],
        operation_name="get chunks for document"
    )
    async def get_chunks_for_document(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get all chunks for a document.
        With graceful degradation - returns empty list if DB unavailable.
        
        Args:
            document_id: Document identifier
            
        Returns:
            List of chunk dicts (empty if DB unavailable)
        """
        chunks = await ChunkRepository.get_chunks_for_document(document_id)
        return [chunk.to_dict() for chunk in chunks]
    
    @graceful_db_operation(
        fallback_value=None,
        operation_name="get chunk by ID"
    )
    async def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Get specific chunk by ID.
        With graceful degradation - returns None if DB unavailable.
        
        Args:
            chunk_id: Chunk identifier
            
        Returns:
            Chunk dict or None if not found or DB unavailable
        """
        # Need to add this to ChunkRepository
        from app.core.db.models import Chunk
        from sqlalchemy import select
        from app.core.db import get_session
        
        async with get_session() as session:
            query = select(Chunk).where(Chunk.id == chunk_id)
            result = await session.execute(query)
            chunk = result.scalar_one_or_none()
            
            if chunk:
                return chunk.to_dict()
            
            return None


# Singleton instance
_document_service = None


def get_document_service() -> DocumentService:
    """
    Get singleton document service instance.
    
    Returns:
        DocumentService instance
    """
    global _document_service
    
    if _document_service is None:
        _document_service = DocumentService()
    
    return _document_service
