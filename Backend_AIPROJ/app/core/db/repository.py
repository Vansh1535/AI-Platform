"""
Document Repository — Database operations for document registry

Provides async CRUD operations for documents, ingestion events, chunks, and cache.
Replaces SQLite operations with PostgreSQL queries.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.models import Document, IngestionEvent, Chunk, CSVInsightsCache
from app.core.db import get_session
from app.core.logging import setup_logger

logger = setup_logger("INFO")


class DocumentRepository:
    """Repository for document operations."""
    
    @staticmethod
    async def create_document(
        document_id: str,
        filename: str,
        file_hash: str,
        file_size: Optional[int] = None,
        file_path: Optional[str] = None,
        mime_type: Optional[str] = None,
        **kwargs
    ) -> Document:
        """
        Create new document in registry.
        
        Args:
            document_id: Unique document identifier
            filename: Original filename
            file_hash: SHA-256 checksum
            file_size: File size in bytes
            file_path: Path to file
            mime_type: MIME type
            **kwargs: Additional document fields
            
        Returns:
            Created Document object
        """
        async with get_session() as session:
            document = Document(
                id=document_id,
                filename=filename,
                file_hash=file_hash,
                file_size=file_size,
                file_path=file_path,
                mime_type=mime_type,
                ingestion_status=kwargs.get("ingestion_status", "pending"),
                ingestion_version=kwargs.get("ingestion_version"),
                ingestion_timestamp=kwargs.get("ingestion_timestamp", datetime.utcnow()),
                processing_time_ms=kwargs.get("processing_time_ms"),
                chunk_count=kwargs.get("chunk_count", 0),
                chunk_strategy=kwargs.get("chunk_strategy"),
                vector_store_ids=kwargs.get("vector_store_ids"),
                embedding_model=kwargs.get("embedding_model"),
                telemetry=kwargs.get("telemetry"),
                graceful_message=kwargs.get("graceful_message"),
                degradation_level=kwargs.get("degradation_level"),
                document_metadata=kwargs.get("document_metadata"),
                tags=kwargs.get("tags"),
            )
            
            session.add(document)
            await session.commit()
            await session.refresh(document)
            
            logger.info(f"✅ Created document: {document_id} ({filename})")
            
            return document
    
    @staticmethod
    async def get_document_by_id(document_id: str) -> Optional[Document]:
        """Get document by ID."""
        async with get_session() as session:
            query = select(Document).where(Document.id == document_id)
            result = await session.execute(query)
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_document_by_hash(file_hash: str) -> Optional[Document]:
        """Get document by file hash (for duplicate detection)."""
        async with get_session() as session:
            query = select(Document).where(Document.file_hash == file_hash)
            result = await session.execute(query)
            return result.scalar_one_or_none()
    
    @staticmethod
    async def list_documents(
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Document]:
        """
        List documents with optional filtering.
        
        Args:
            status: Filter by ingestion_status
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of Document objects
        """
        async with get_session() as session:
            query = select(Document).order_by(Document.created_at.desc())
            
            if status:
                query = query.where(Document.ingestion_status == status)
            
            query = query.limit(limit).offset(offset)
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    @staticmethod
    async def update_document(
        document_id: str,
        **kwargs
    ) -> Optional[Document]:
        """
        Update document fields.
        
        Args:
            document_id: Document to update
            **kwargs: Fields to update
            
        Returns:
            Updated Document object or None if not found
        """
        async with get_session() as session:
            query = select(Document).where(Document.id == document_id)
            result = await session.execute(query)
            document = result.scalar_one_or_none()
            
            if not document:
                logger.warning(f"Document not found: {document_id}")
                return None
            
            # Update fields
            for key, value in kwargs.items():
                if hasattr(document, key):
                    setattr(document, key, value)
            
            document.updated_at = datetime.utcnow()
            
            await session.commit()
            await session.refresh(document)
            
            logger.info(f"✅ Updated document: {document_id}")
            
            return document
    
    @staticmethod
    async def delete_document(document_id: str) -> bool:
        """Delete document (cascades to chunks and events)."""
        async with get_session() as session:
            query = delete(Document).where(Document.id == document_id)
            result = await session.execute(query)
            await session.commit()
            
            deleted = result.rowcount > 0
            
            if deleted:
                logger.info(f"✅ Deleted document: {document_id}")
            else:
                logger.warning(f"Document not found for deletion: {document_id}")
            
            return deleted
    
    @staticmethod
    async def count_documents(status: Optional[str] = None) -> int:
        """Count total documents, optionally filtered by status."""
        async with get_session() as session:
            query = select(func.count()).select_from(Document)
            
            if status:
                query = query.where(Document.ingestion_status == status)
            
            result = await session.execute(query)
            return result.scalar()


class IngestionEventRepository:
    """Repository for ingestion event operations."""
    
    @staticmethod
    async def create_event(
        document_id: str,
        event_type: str,
        event_status: str,
        **kwargs
    ) -> IngestionEvent:
        """
        Create ingestion event.
        
        Args:
            document_id: Associated document ID
            event_type: Type of event (ingestion_started, completed, failed, etc.)
            event_status: Status (success, failure, warning)
            **kwargs: Additional event fields
            
        Returns:
            Created IngestionEvent object
        """
        async with get_session() as session:
            event = IngestionEvent(
                document_id=document_id,
                event_type=event_type,
                event_status=event_status,
                event_timestamp=kwargs.get("event_timestamp", datetime.utcnow()),
                processing_time_ms=kwargs.get("processing_time_ms"),
                chunks_created=kwargs.get("chunks_created"),
                bytes_processed=kwargs.get("bytes_processed"),
                error_message=kwargs.get("error_message"),
                error_type=kwargs.get("error_type"),
                telemetry=kwargs.get("telemetry"),
                graceful_message=kwargs.get("graceful_message"),
                degradation_level=kwargs.get("degradation_level"),
                ingestion_mode=kwargs.get("ingestion_mode"),
                triggered_by=kwargs.get("triggered_by", "system"),
            )
            
            session.add(event)
            await session.commit()
            await session.refresh(event)
            
            logger.debug(f"Created ingestion event: {event_type} for {document_id}")
            
            return event
    
    @staticmethod
    async def get_events_for_document(document_id: str) -> List[IngestionEvent]:
        """Get all ingestion events for a document."""
        async with get_session() as session:
            query = select(IngestionEvent).where(
                IngestionEvent.document_id == document_id
            ).order_by(IngestionEvent.event_timestamp.desc())
            
            result = await session.execute(query)
            return list(result.scalars().all())


class ChunkRepository:
    """Repository for chunk operations."""
    
    @staticmethod
    async def create_chunk(
        chunk_id: str,
        document_id: str,
        chunk_index: int,
        **kwargs
    ) -> Chunk:
        """Create chunk record."""
        async with get_session() as session:
            chunk = Chunk(
                id=chunk_id,
                document_id=document_id,
                chunk_index=chunk_index,
                chunk_text=kwargs.get("chunk_text"),
                chunk_size=kwargs.get("chunk_size"),
                vector_id=kwargs.get("vector_id"),
                embedding_model=kwargs.get("embedding_model"),
                embedding_dim=kwargs.get("embedding_dim"),
                chunk_strategy=kwargs.get("chunk_strategy"),
                overlap_size=kwargs.get("overlap_size"),
                chunk_metadata=kwargs.get("chunk_metadata"),
            )
            
            session.add(chunk)
            await session.commit()
            await session.refresh(chunk)
            
            return chunk
    
    @staticmethod
    async def get_chunks_for_document(document_id: str) -> List[Chunk]:
        """Get all chunks for a document."""
        async with get_session() as session:
            query = select(Chunk).where(
                Chunk.document_id == document_id
            ).order_by(Chunk.chunk_index)
            
            result = await session.execute(query)
            return list(result.scalars().all())


class CSVCacheRepository:
    """Repository for CSV insights cache operations."""
    
    @staticmethod
    async def get_cached_insights(
        document_id: str,
        config_hash: str,
        analysis_mode: str = "light",
        enable_llm_insights: bool = False
    ) -> Optional[CSVInsightsCache]:
        """Get cached CSV insights by normalized cache key."""
        try:
            logger.info(f"🔍 Cache lookup - doc:{document_id}, config:{config_hash[:8]}..., mode:{analysis_mode}, llm:{enable_llm_insights}")
            
            async with get_session() as session:
                query = select(CSVInsightsCache).where(
                    and_(
                        CSVInsightsCache.file_hash == config_hash[:64],  # Use config_hash as cache key
                        CSVInsightsCache.dataset_name == document_id,
                        CSVInsightsCache.analysis_mode == analysis_mode,
                        CSVInsightsCache.enable_llm_insights == enable_llm_insights
                    )
                )
                
                result = await session.execute(query)
                cache_entry = result.scalar_one_or_none()
                
                if cache_entry:
                    # Validate cache entry integrity
                    if not cache_entry.insights_data:
                        logger.warning(f"⚠️ Cache entry corrupt for {document_id} - will recompute")
                        return None
                    
                    # Update access stats with proper transaction
                    async with session.begin():
                        cache_entry.accessed_at = datetime.utcnow()
                        cache_entry.access_count += 1
                        await session.flush()
                    
                    logger.info(f"✅ Cache HIT for document {document_id[:16]}... (config={config_hash[:8]}...)")
                else:
                    logger.info(f"❌ Cache MISS for document {document_id[:16]}... (config={config_hash[:8]}...)")
                
                return cache_entry
        except Exception as e:
            logger.warning(f"⚠️ Cache lookup failed for {document_id}: {str(e)}")
            return None
    
    @staticmethod
    async def save_to_cache(
        document_id: str,
        config_hash: str,
        analysis_mode: str,
        enable_llm_insights: bool,
        insights_data: Dict[str, Any],
        **kwargs
    ) -> Optional[CSVInsightsCache]:
        """Save CSV insights to cache with normalized keys."""
        try:
            logger.info(f"💾 Cache save - doc:{document_id}, config:{config_hash[:8]}..., mode:{analysis_mode}, llm:{enable_llm_insights}")
            
            async with get_session() as session:
                # Check for existing entry and update or create new
                existing_query = select(CSVInsightsCache).where(
                    and_(
                        CSVInsightsCache.file_hash == config_hash[:64],
                        CSVInsightsCache.dataset_name == document_id,
                        CSVInsightsCache.analysis_mode == analysis_mode,
                        CSVInsightsCache.enable_llm_insights == enable_llm_insights
                    )
                )
                
                result = await session.execute(existing_query)
                cache_entry = result.scalar_one_or_none()
                
                # Ensure transaction commits properly with single session
                async with session.begin():
                    if cache_entry:
                        # Update existing entry
                        cache_entry.insights_data = insights_data
                        cache_entry.telemetry = kwargs.get("telemetry")
                        cache_entry.accessed_at = datetime.utcnow()
                        cache_entry.expires_at = kwargs.get("expires_at")
                    else:
                        # Create new entry
                        cache_entry = CSVInsightsCache(
                            file_hash=config_hash[:64],  # Use config_hash as cache key
                            analysis_mode=analysis_mode,
                            enable_llm_insights=enable_llm_insights,
                            insights_data=insights_data,
                            dataset_name=document_id,  # Use document_id as dataset_name
                            telemetry=kwargs.get("telemetry"),
                            row_count=kwargs.get("row_count"),
                            column_count=kwargs.get("column_count"),
                            computation_time_ms=kwargs.get("computation_time_ms"),
                            expires_at=kwargs.get("expires_at"),
                        )
                        session.add(cache_entry)
                    
                    await session.flush()
                
                # Refresh the object to get updated values
                await session.refresh(cache_entry)
                
                logger.info(f"✅ Saved to cache: document {document_id[:16]}... (config={config_hash[:8]}...)")
                
                return cache_entry
        except Exception as e:
            logger.error(f"❌ Failed to save to cache for {document_id}: {str(e)}")
            return None
