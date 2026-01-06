"""
Document registry for tracking ingestion metadata and health.
Provides persistent storage using SQLite with full audit trail.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from app.core.logging import setup_logger

logger = setup_logger("INFO")


class DocumentRegistry:
    """
    Persistent document registry tracking ingestion metadata, versions, and health.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the document registry.
        
        Args:
            db_path: Path to SQLite database (defaults to ./data/document_registry.db)
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent.parent / "data" / "document_registry.db"
        
        self.db_path = db_path
        self._init_database()
        logger.info(f"Document registry initialized at {db_path}")
    
    def _init_database(self):
        """Initialize SQLite database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                page_count INTEGER,
                chunk_count INTEGER,
                token_estimate INTEGER,
                checksum_hash TEXT NOT NULL,
                ingestion_status TEXT NOT NULL,
                ingestion_version INTEGER DEFAULT 1,
                exists_policy TEXT DEFAULT 'skip',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                processing_time_ms INTEGER,
                chunk_size INTEGER,
                overlap INTEGER,
                tokenizer_name TEXT,
                source_path TEXT,
                failure_reason TEXT
            )
        """)
        
        # Create index on checksum for fast duplicate lookup
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_checksum 
            ON documents(checksum_hash)
        """)
        
        # Create index on status for health queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status 
            ON documents(ingestion_status)
        """)
        
        conn.commit()
        conn.close()
        logger.info("Database schema initialized")
    
    def register_ingestion_start(
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
        Register the start of a document ingestion.
        
        Args:
            document_id: Unique document identifier
            filename: Original filename
            file_type: File type (pdf, txt, etc.)
            file_size_bytes: File size in bytes
            checksum_hash: SHA-256 checksum
            source_path: Source file path
            chunk_size: Chunking configuration
            overlap: Chunk overlap size
            tokenizer_name: Tokenizer used
            exists_policy: Policy for existing documents (skip/overwrite/version_as_new)
        
        Returns:
            dict: Registration metadata
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        
        try:
            cursor.execute("""
                INSERT INTO documents (
                    document_id, filename, file_type, file_size_bytes,
                    checksum_hash, ingestion_status, created_at, updated_at,
                    chunk_size, overlap, tokenizer_name, source_path, exists_policy
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                document_id, filename, file_type, file_size_bytes,
                checksum_hash, "processing", now, now,
                chunk_size, overlap, tokenizer_name, source_path, exists_policy
            ))
            
            conn.commit()
            logger.info(f"Registered ingestion start: {document_id} ({filename})")
            
            return {
                "document_id": document_id,
                "status": "processing",
                "created_at": now
            }
        
        except sqlite3.IntegrityError:
            logger.warning(f"Document {document_id} already exists in registry")
            return {"error": "Document already exists", "document_id": document_id}
        
        finally:
            conn.close()
    
    def register_ingestion_success(
        self,
        document_id: str,
        page_count: int,
        chunk_count: int,
        token_estimate: int,
        processing_time_ms: int
    ) -> Dict[str, Any]:
        """
        Mark ingestion as successful and update metadata.
        
        Args:
            document_id: Document identifier
            page_count: Number of pages processed
            chunk_count: Number of chunks created
            token_estimate: Estimated token count
            processing_time_ms: Processing time in milliseconds
        
        Returns:
            dict: Updated metadata
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        
        cursor.execute("""
            UPDATE documents
            SET ingestion_status = ?,
                page_count = ?,
                chunk_count = ?,
                token_estimate = ?,
                processing_time_ms = ?,
                updated_at = ?,
                failure_reason = NULL
            WHERE document_id = ?
        """, ("success", page_count, chunk_count, token_estimate, processing_time_ms, now, document_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Registered ingestion success: {document_id} ({chunk_count} chunks, {processing_time_ms}ms)")
        
        return {
            "document_id": document_id,
            "status": "success",
            "chunk_count": chunk_count,
            "processing_time_ms": processing_time_ms
        }
    
    def register_ingestion_failure(
        self,
        document_id: str,
        failure_reason: str,
        processing_time_ms: int
    ) -> Dict[str, Any]:
        """
        Mark ingestion as failed with reason.
        
        Args:
            document_id: Document identifier
            failure_reason: Reason for failure
            processing_time_ms: Processing time before failure
        
        Returns:
            dict: Failure metadata
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        
        cursor.execute("""
            UPDATE documents
            SET ingestion_status = ?,
                failure_reason = ?,
                processing_time_ms = ?,
                updated_at = ?
            WHERE document_id = ?
        """, ("failed", failure_reason, processing_time_ms, now, document_id))
        
        conn.commit()
        conn.close()
        
        logger.error(f"Registered ingestion failure: {document_id} - {failure_reason}")
        
        return {
            "document_id": document_id,
            "status": "failed",
            "failure_reason": failure_reason
        }
    
    def get_document_meta(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full metadata for a document.
        
        Args:
            document_id: Document identifier
        
        Returns:
            dict: Document metadata or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM documents WHERE document_id = ?", (document_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row is None:
            return None
        
        return dict(row)
    
    def find_by_checksum(self, checksum_hash: str) -> List[Dict[str, Any]]:
        """
        Find documents by checksum hash.
        
        Args:
            checksum_hash: SHA-256 checksum
        
        Returns:
            list: List of matching documents
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM documents WHERE checksum_hash = ?", (checksum_hash,))
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def list_documents(
        self,
        status_filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List documents with optional filtering.
        
        Args:
            status_filter: Filter by status (success/failed/processing)
            limit: Maximum number of results
            offset: Pagination offset
        
        Returns:
            dict: Documents list with metadata
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get total count
        if status_filter:
            cursor.execute("SELECT COUNT(*) FROM documents WHERE ingestion_status = ?", (status_filter,))
        else:
            cursor.execute("SELECT COUNT(*) FROM documents")
        
        total_count = cursor.fetchone()[0]
        
        # Get documents
        if status_filter:
            cursor.execute("""
                SELECT * FROM documents 
                WHERE ingestion_status = ?
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """, (status_filter, limit, offset))
        else:
            cursor.execute("""
                SELECT * FROM documents 
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
        
        rows = cursor.fetchall()
        
        # Get health summary
        cursor.execute("""
            SELECT 
                ingestion_status,
                COUNT(*) as count,
                AVG(processing_time_ms) as avg_time_ms,
                SUM(chunk_count) as total_chunks
            FROM documents
            GROUP BY ingestion_status
        """)
        
        health_rows = cursor.fetchall()
        health_summary = {row["ingestion_status"]: dict(row) for row in health_rows}
        
        conn.close()
        
        return {
            "documents": [dict(row) for row in rows],
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "health_summary": health_summary
        }
    
    def increment_version(self, document_id: str) -> int:
        """
        Increment document version number.
        
        Args:
            document_id: Document identifier
        
        Returns:
            int: New version number
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE documents
            SET ingestion_version = ingestion_version + 1
            WHERE document_id = ?
        """, (document_id,))
        
        cursor.execute("""
            SELECT ingestion_version FROM documents WHERE document_id = ?
        """, (document_id,))
        
        version = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        
        logger.info(f"Incremented version for {document_id} to v{version}")
        return version


# Singleton instance
_registry: Optional[DocumentRegistry] = None


def get_registry() -> DocumentRegistry:
    """
    Get or create the singleton document registry.
    
    Returns:
        DocumentRegistry: The registry instance
    """
    global _registry
    if _registry is None:
        _registry = DocumentRegistry()
    return _registry
