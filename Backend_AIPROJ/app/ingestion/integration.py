"""
Multi-file ingestion integration layer.
DEPRECATED: This module provides backward compatibility only.
Use integration_async.py for new code with PostgreSQL support.
"""

from pathlib import Path
from typing import Optional, Dict, Any
import time
import asyncio
from app.core.logging import setup_logger

logger = setup_logger()


def ingest_multi_file(
    file_path: str,
    source: str,
    chunk_size: int = 200,
    overlap: int = 50,
    exists_policy: str = "skip",
    normalize: bool = True
) -> Dict[str, Any]:
    """
    SYNC WRAPPER for backward compatibility with existing tests.
    
    This function wraps the async PostgreSQL-backed ingestion pipeline
    and provides a synchronous interface for legacy code.
    
    NEW CODE SHOULD USE: ingest_multi_file_async() directly
    
    Args:
        file_path: Path to the file
        source: Source identifier for the document
        chunk_size: Size of text chunks (default: 200)
        overlap: Overlap between chunks (default: 50)
        exists_policy: Policy for existing documents - skip/overwrite/version_as_new (default: skip)
        normalize: Apply content normalization (default: True)
        
    Returns:
        Ingestion result with status, chunk count, metadata, and document_id
    """
    from app.ingestion.integration_async import ingest_multi_file_async
    
    try:
        # Run async function in sync context
        result = asyncio.run(
            ingest_multi_file_async(
                file_path=file_path,
                source=source,
                chunk_size=chunk_size,
                overlap=overlap,
                exists_policy=exists_policy,
                normalize=normalize
            )
        )
        return result
    except Exception as e:
        logger.error(f"Sync wrapper failed: {str(e)}")
        return {
            "status": "failed",
            "chunks": 0,
            "message": str(e),
            "degradation_level": "sync_wrapper_error",
            "fallback_triggered": True
        }
