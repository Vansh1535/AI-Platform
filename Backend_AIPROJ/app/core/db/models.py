"""
Database Models — Registry Tables for RAG Platform

Replaces SQLite registry with PostgreSQL tables.

Tables:
- documents: Document metadata and ingestion status
- ingestion_events: Audit trail of ingestion operations
- chunks: Document chunks for vector store tracking
- csv_insights_cache: Cache for CSV analytics

Design:
- Preserves all SQLite fields
- Adds indexes for performance
- Maintains backward compatibility
- Supports all existing queries
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.db.postgres import Base


class Document(Base):
    """
    Document registry table.
    
    Tracks all ingested documents with metadata, status, and telemetry.
    Replaces SQLite document registry.
    """
    __tablename__ = "documents"
    
    # Primary key
    id = Column(String(255), primary_key=True, index=True)  # document_id
    
    # File metadata
    filename = Column(String(500), nullable=False, index=True)
    file_path = Column(Text, nullable=True)
    file_size = Column(Integer, nullable=True)  # bytes
    file_hash = Column(String(64), nullable=False, index=True)  # SHA-256 checksum
    mime_type = Column(String(100), nullable=True)
    
    # Ingestion metadata
    ingestion_status = Column(String(50), nullable=False, default="pending", index=True)
    # Status values: pending, processing, completed, failed
    
    ingestion_version = Column(String(20), nullable=True)  # e.g., "v1.2.0"
    ingestion_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    processing_time_ms = Column(Integer, nullable=True)  # milliseconds
    
    # Chunk tracking
    chunk_count = Column(Integer, nullable=False, default=0)
    chunk_strategy = Column(String(50), nullable=True)  # e.g., "fixed_size", "semantic"
    
    # Vector store metadata
    vector_store_ids = Column(JSON, nullable=True)  # List of vector IDs
    embedding_model = Column(String(100), nullable=True)
    
    # Telemetry and observability
    telemetry = Column(JSON, nullable=True)  # Full telemetry context
    graceful_message = Column(Text, nullable=True)  # Degradation messages
    degradation_level = Column(String(50), nullable=True)  # none, partial, fallback
    
    # Metadata
    document_metadata = Column(JSON, nullable=True)  # Custom metadata
    tags = Column(JSON, nullable=True)  # Document tags
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ingestion_events = relationship("IngestionEvent", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_documents_status_timestamp', 'ingestion_status', 'ingestion_timestamp'),
        Index('idx_documents_hash', 'file_hash'),
    )
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        # Extract format from mime_type for frontend compatibility
        format_str = "unknown"
        if self.mime_type:
            if "pdf" in self.mime_type:
                format_str = "pdf"
            elif "csv" in self.mime_type:
                format_str = "csv"
            elif "text" in self.mime_type or "plain" in self.mime_type:
                format_str = "txt"
            elif "word" in self.mime_type or "docx" in self.mime_type:
                format_str = "docx"
            elif "markdown" in self.mime_type:
                format_str = "md"
        
        return {
            "id": self.id,
            "filename": self.filename,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "file_hash": self.file_hash,
            "mime_type": self.mime_type,
            "format": format_str,  # Frontend expects this field
            "status": self.ingestion_status,  # Frontend expects 'status' not 'ingestion_status'
            "ingestion_status": self.ingestion_status,
            "ingestion_version": self.ingestion_version,
            "ingestion_timestamp": self.ingestion_timestamp.isoformat() if self.ingestion_timestamp else None,
            "processing_time_ms": self.processing_time_ms,
            "chunk_count": self.chunk_count,
            "chunk_strategy": self.chunk_strategy,
            "vector_store_ids": self.vector_store_ids,
            "embedding_model": self.embedding_model,
            "telemetry": self.telemetry,
            "graceful_message": self.graceful_message,
            "degradation_level": self.degradation_level,
            "document_metadata": self.document_metadata,
            "tags": self.tags,
            "source": self.file_path or "upload",  # Frontend expects 'source' field
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class IngestionEvent(Base):
    """
    Ingestion audit trail table.
    
    Records every ingestion operation for observability and debugging.
    Supports multiple events per document (re-ingestion tracking).
    """
    __tablename__ = "ingestion_events"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to document
    document_id = Column(String(255), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Event metadata
    event_type = Column(String(50), nullable=False, index=True)
    # Types: ingestion_started, ingestion_completed, ingestion_failed, re_ingestion, update
    
    event_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    event_status = Column(String(50), nullable=False)  # success, failure, warning
    
    # Processing details
    processing_time_ms = Column(Integer, nullable=True)
    chunks_created = Column(Integer, nullable=True)
    bytes_processed = Column(Integer, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    error_type = Column(String(100), nullable=True)
    
    # Telemetry
    telemetry = Column(JSON, nullable=True)
    graceful_message = Column(Text, nullable=True)
    degradation_level = Column(String(50), nullable=True)
    
    # Additional context
    ingestion_mode = Column(String(50), nullable=True)  # full, incremental, refresh
    triggered_by = Column(String(100), nullable=True)  # user, system, api
    
    # Relationship
    document = relationship("Document", back_populates="ingestion_events")
    
    # Indexes
    __table_args__ = (
        Index('idx_events_document_timestamp', 'document_id', 'event_timestamp'),
        Index('idx_events_type_status', 'event_type', 'event_status'),
    )
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "event_type": self.event_type,
            "event_timestamp": self.event_timestamp.isoformat() if self.event_timestamp else None,
            "event_status": self.event_status,
            "processing_time_ms": self.processing_time_ms,
            "chunks_created": self.chunks_created,
            "bytes_processed": self.bytes_processed,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "telemetry": self.telemetry,
            "graceful_message": self.graceful_message,
            "degradation_level": self.degradation_level,
            "ingestion_mode": self.ingestion_mode,
            "triggered_by": self.triggered_by,
        }


class Chunk(Base):
    """
    Chunk registry table.
    
    Tracks document chunks for vector store mapping.
    Enables chunk-level analytics and debugging.
    """
    __tablename__ = "chunks"
    
    # Primary key
    id = Column(String(255), primary_key=True, index=True)  # chunk_id
    
    # Foreign key to document
    document_id = Column(String(255), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Chunk metadata
    chunk_index = Column(Integer, nullable=False)  # 0-based index
    chunk_text = Column(Text, nullable=True)  # Optional: store actual text
    chunk_size = Column(Integer, nullable=True)  # characters or tokens
    
    # Vector store mapping
    vector_id = Column(String(255), nullable=True, index=True)  # ID in vector store
    embedding_model = Column(String(100), nullable=True)
    embedding_dim = Column(Integer, nullable=True)
    
    # Chunk strategy
    chunk_strategy = Column(String(50), nullable=True)
    overlap_size = Column(Integer, nullable=True)
    
    # Metadata
    chunk_metadata = Column(JSON, nullable=True)  # Custom metadata
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship
    document = relationship("Document", back_populates="chunks")
    
    # Indexes
    __table_args__ = (
        Index('idx_chunks_document_index', 'document_id', 'chunk_index'),
        Index('idx_chunks_vector_id', 'vector_id'),
    )
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "chunk_size": self.chunk_size,
            "vector_id": self.vector_id,
            "embedding_model": self.embedding_model,
            "embedding_dim": self.embedding_dim,
            "chunk_strategy": self.chunk_strategy,
            "overlap_size": self.overlap_size,
            "chunk_metadata": self.chunk_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CSVInsightsCache(Base):
    """
    CSV insights cache table.
    
    Caches CSV analytics results to avoid re-computation.
    Keyed by file hash for deduplication.
    """
    __tablename__ = "csv_insights_cache"
    
    # Primary key (file hash + mode)
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_hash = Column(String(64), nullable=False, index=True)
    
    # Cache key components
    dataset_name = Column(String(500), nullable=True)
    analysis_mode = Column(String(50), nullable=False)  # light, full
    enable_llm_insights = Column(Boolean, nullable=False, default=False)
    
    # Cached results
    insights_data = Column(JSON, nullable=False)  # Full insights result
    telemetry = Column(JSON, nullable=True)
    
    # Cache metadata
    row_count = Column(Integer, nullable=True)
    column_count = Column(Integer, nullable=True)
    computation_time_ms = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    accessed_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    access_count = Column(Integer, nullable=False, default=1)
    
    # Expiry (optional)
    expires_at = Column(DateTime, nullable=True, index=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_cache_hash_mode', 'file_hash', 'analysis_mode', 'enable_llm_insights', unique=True),
        Index('idx_cache_expires', 'expires_at'),
    )
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "file_hash": self.file_hash,
            "dataset_name": self.dataset_name,
            "analysis_mode": self.analysis_mode,
            "enable_llm_insights": self.enable_llm_insights,
            "insights_data": self.insights_data,
            "telemetry": self.telemetry,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "computation_time_ms": self.computation_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "accessed_at": self.accessed_at.isoformat() if self.accessed_at else None,
            "access_count": self.access_count,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
