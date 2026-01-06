"""
Async multi-file ingestion integration layer.
PostgreSQL-backed version with async/await throughout.
"""

from pathlib import Path
from typing import Optional, Dict, Any
import time
from app.core.logging import setup_logger
from app.core.db.document_service import get_document_service
from app.core.db import ChunkRepository
from app.core.db.graceful import safe_db_call
from app.rag.ingestion.validators import validate_document_for_ingestion, ValidationError
from app.rag.ingestion.checksum import compute_file_checksum, generate_document_id
from app.rag.ingestion.ingest import get_embedding_model, get_chroma_collection
from app.ingestion.dispatcher import dispatch_file
from app.ingestion.normalize import normalize_content

logger = setup_logger()


async def check_duplicate_policy_async(
    checksum: str,
    exists_policy: str
) -> Dict[str, Any]:
    """
    Check duplicate policy using PostgreSQL registry.
    
    Args:
        checksum: File SHA-256 checksum
        exists_policy: Policy for existing documents (skip/overwrite/version_as_new)
        
    Returns:
        dict with action and existing_docs
    """
    service = get_document_service()
    
    # Check if document exists
    existing_doc = await service.get_document_by_checksum(checksum)
    
    if not existing_doc:
        return {"action": "proceed", "version": 1, "existing_docs": []}
    
    # Document exists - apply policy
    if exists_policy == "skip":
        return {
            "action": "skip",
            "version": existing_doc.get("ingestion_version", 1),
            "existing_docs": [existing_doc]
        }
    
    elif exists_policy == "overwrite":
        return {
            "action": "proceed",
            "version": existing_doc.get("ingestion_version", 1),
            "existing_docs": [existing_doc],
            "overwrite": True
        }
    
    elif exists_policy == "version_as_new":
        new_version = existing_doc.get("ingestion_version", 1) + 1
        return {
            "action": "proceed",
            "version": new_version,
            "existing_docs": [existing_doc]
        }
    
    # Default to skip
    return {
        "action": "skip",
        "version": existing_doc.get("ingestion_version", 1),
        "existing_docs": [existing_doc]
    }


async def ingest_multi_file_async(
    file_path: str,
    source: str,
    chunk_size: int = 200,
    overlap: int = 50,
    exists_policy: str = "skip",
    normalize: bool = True
) -> Dict[str, Any]:
    """
    Async version of multi-file ingestion using PostgreSQL.
    
    This function:
    1. Dispatches to appropriate parser
    2. Normalizes content
    3. Feeds into existing chunking + embedding + registry pipeline
    4. Uses PostgreSQL for document tracking
    
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
    start_time = time.time()
    service = get_document_service()
    document_id = None
    
    try:
        logger.info(
            f"Starting async multi-file ingestion pipeline - "
            f"File: {file_path}, Source: {source}, Policy: {exists_policy}"
        )
        
        # Step 1: Validate file exists and get basic info
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size_bytes = path.stat().st_size
        
        # Step 2: Compute Checksum
        logger.info("Step 2: Computing file checksum...")
        checksum = compute_file_checksum(file_path)
        
        # Step 3: Check for Duplicates (async)
        logger.info("Step 3: Checking duplicate policy...")
        duplicate_check = await check_duplicate_policy_async(checksum, exists_policy)
        
        if duplicate_check["action"] == "skip":
            processing_time = int((time.time() - start_time) * 1000)
            existing_doc = duplicate_check["existing_docs"][0]
            logger.info(f"Skipping duplicate document: {existing_doc['id']}")
            return {
                "status": "skipped",
                "reason": "duplicate_exists",
                "document_id": existing_doc["id"],
                "chunks": existing_doc.get("chunk_count", 0),
                "processing_time_ms": processing_time,
                "existing_document": existing_doc
            }
        
        # Step 4: Parse file using dispatcher
        logger.info("Step 4: Parsing file...")
        try:
            parsed_doc = dispatch_file(file_path, source)
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"File parsing failed: {str(e)}")
            return {
                "status": "failed",
                "chunks": 0,
                "message": f"Parsing failed: {str(e)}",
                "processing_time_ms": processing_time,
                "format": Path(file_path).suffix
            }
        
        # Step 5: Normalize content if requested
        if normalize:
            logger.info("Step 5: Normalizing content...")
            original_length = len(parsed_doc.text)
            parsed_doc.text = normalize_content(parsed_doc.text)
            logger.info(
                f"Content normalized: {original_length} -> {len(parsed_doc.text)} chars"
            )
        
        # Step 6: Generate Document ID
        version = duplicate_check.get("version", 1)
        document_id = generate_document_id(
            path.name,
            checksum,
            version
        )
        
        # Step 7: Register Ingestion Start (with graceful degradation)
        logger.info(f"Step 7: Registering ingestion start for document: {document_id}")
        reg_result = await service.register_ingestion_start(
            document_id=document_id,
            filename=path.name,
            file_type=parsed_doc.format,
            file_size_bytes=file_size_bytes,
            checksum_hash=checksum,
            source_path=file_path,
            chunk_size=chunk_size,
            overlap=overlap,
            tokenizer_name="character",
            exists_policy=exists_policy
        )
        
        # Check if DB registration failed but continue anyway
        db_degraded = reg_result.get("degradation_level") == "fallback"
        if db_degraded:
            logger.warning("⚠️ Database unavailable - continuing with vector-only ingestion")
        
        # Step 8: Chunk the text
        logger.info("Step 8: Chunking text...")
        
        # Use character-based chunking for non-PDF files
        chunks_data = create_text_chunks(
            text=parsed_doc.text,
            source=source,
            chunk_size=chunk_size,
            overlap=overlap
        )
        
        num_chunks = len(chunks_data)
        logger.info(f"Created {num_chunks} chunks from {len(parsed_doc.text)} chars")
        
        if num_chunks == 0:
            processing_time = int((time.time() - start_time) * 1000)
            await service.register_ingestion_failure(
                document_id=document_id,
                failure_reason="No chunks created from document",
                processing_time_ms=processing_time
            )
            return {
                "status": "failed",
                "document_id": document_id,
                "chunks": 0,
                "message": "No chunks created from document",
                "processing_time_ms": processing_time,
                "format": parsed_doc.format
            }
        
        # Step 9: Enrich chunk metadata with parsed document metadata
        logger.info(f"Step 9: Enriching chunk metadata...")
        
        # Step 9.1: For CSV files, store complex metadata in PostgreSQL to avoid ChromaDB list errors
        if parsed_doc.format == "csv":
            logger.info("Step 9.1: Detected CSV file - storing metadata in PostgreSQL...")
            try:
                from app.analytics.csv_metadata import extract_csv_metadata_for_storage, save_csv_metadata_to_db
                
                # Extract metadata from parsed CSV data
                if hasattr(parsed_doc, 'dataframe') and parsed_doc.dataframe is not None:
                    csv_meta = extract_csv_metadata_for_storage(parsed_doc.dataframe)
                    
                    # Store in PostgreSQL
                    meta_saved = await save_csv_metadata_to_db(
                        document_id=document_id,
                        schema=csv_meta["schema"],
                        column_stats=csv_meta["column_stats"],
                        row_count=csv_meta["row_count"],
                        column_count=csv_meta["column_count"],
                        sample_rows=csv_meta.get("sample_rows", []),
                        data_quality=csv_meta.get("data_quality", {})
                    )
                    
                    if meta_saved:
                        logger.info(f"✅ CSV metadata stored in PostgreSQL for {document_id}")
                    else:
                        logger.warning(f"⚠️ Failed to store CSV metadata in PostgreSQL - will recompute on demand")
                else:
                    logger.warning("CSV file has no dataframe - skipping metadata storage")
                    
            except Exception as e:
                logger.warning(f"⚠️ CSV metadata storage failed: {str(e)} - continuing without stored metadata")
        
        # Step 9.2: Add base metadata to all chunks
        for chunk in chunks_data:
            chunk["metadata"].update({
                "document_id": document_id,  # Add document_id for filtering
                "format": parsed_doc.format,
                "source_type": parsed_doc.source_type,
                "ingestion_method": "multi_file_ingest_postgres_v1"
            })
            
            # For CSV files, only add simple metadata to avoid ChromaDB list errors
            if parsed_doc.format == "csv":
                # Add only row index for CSV chunks (complex metadata in PostgreSQL)
                chunk["metadata"]["row_index"] = chunk["metadata"].get("chunk_index", 0)
            else:
                # For non-CSV files, add custom metadata from parser
                if parsed_doc.metadata:
                    for key, value in parsed_doc.metadata.items():
                        if key not in chunk["metadata"]:
                            # Skip list/dict types to be safe
                            if isinstance(value, (str, int, float, bool)) or value is None:
                                chunk["metadata"][key] = value
        
        # Step 10: Generate embeddings and store
        logger.info("Step 10: Generating embeddings...")
        model = get_embedding_model()
        collection = get_chroma_collection()
        
        chunk_texts = [chunk["text"] for chunk in chunks_data]
        chunk_metadatas = [chunk["metadata"] for chunk in chunks_data]
        
        embeddings = model.encode(chunk_texts).tolist()
        
        # Generate unique IDs for chunks
        ids = [f"{document_id}_chunk_{i}" for i in range(num_chunks)]
        
        # Store in Chroma with full metadata
        logger.info("Step 11: Storing in vector database...")
        collection.add(
            embeddings=embeddings,
            documents=chunk_texts,
            ids=ids,
            metadatas=chunk_metadatas
        )
        
        # Step 11.5: Persist chunks to PostgreSQL (with graceful degradation)
        logger.info("Step 11.5: Persisting chunks to database...")
        for i, (chunk_id, chunk_data) in enumerate(zip(ids, chunks_data)):
            try:
                await ChunkRepository.create_chunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    chunk_index=i,
                    chunk_text=chunk_data["text"][:1000] if len(chunk_data["text"]) > 1000 else chunk_data["text"],  # Store first 1000 chars for preview
                    chunk_size=len(chunk_data["text"]),
                    vector_id=chunk_id,
                    embedding_model="sentence-transformers/all-MiniLM-L6-v2",
                    embedding_dim=384,
                    chunk_strategy="fixed_size",
                    overlap_size=overlap,
                    chunk_metadata=chunk_data["metadata"]
                )
            except Exception as e:
                logger.warning(f"⚠️ Failed to persist chunk {i} to database: {str(e)} - continuing without DB tracking")
        
        logger.info(f"✅ Persisted {num_chunks} chunks to database (with graceful degradation if needed)")
        
        # Step 12: Estimate tokens
        total_chars = sum(len(text) for text in chunk_texts)
        token_estimate = total_chars // 4
        
        # Step 13: Register success (async with graceful degradation)
        processing_time = int((time.time() - start_time) * 1000)
        logger.info(f"Step 13: Registering ingestion success...")
        success_result = await service.register_ingestion_success(
            document_id=document_id,
            page_count=parsed_doc.metadata.get("page_count", 0),
            chunk_count=num_chunks,
            token_estimate=token_estimate,
            processing_time_ms=processing_time
        )
        
        # Check if success registration degraded
        success_degraded = success_result.get("degradation_level") == "fallback"
        
        logger.info(
            f"Async multi-file ingestion complete: {document_id} - "
            f"{num_chunks} chunks ({parsed_doc.format.upper()}) in {processing_time}ms"
        )
        
        # Build response with degradation info
        response = {
            "status": "success",
            "document_id": document_id,
            "chunks": num_chunks,
            "format": parsed_doc.format,
            "source_type": parsed_doc.source_type,
            "token_estimate": token_estimate,
            "processing_time_ms": processing_time,
            "checksum": checksum,
            "version": version,
            "metadata": parsed_doc.metadata
        }
        
        # Add degradation info if DB was unavailable
        if db_degraded or success_degraded:
            response["degradation_level"] = "partial"
            response["fallback_triggered"] = True
            response["graceful_message"] = "Document ingested into vector store successfully, but database tracking unavailable"
            response["routing_decision"] = "db_fallback"
        
        return response
        
    except FileNotFoundError as e:
        processing_time = int((time.time() - start_time) * 1000)
        logger.error(f"File not found: {str(e)}")
        return {
            "status": "failed",
            "chunks": 0,
            "message": str(e),
            "processing_time_ms": processing_time
        }
    
    except Exception as e:
        processing_time = int((time.time() - start_time) * 1000)
        logger.error(f"Async multi-file ingestion failed: {str(e)}")
        
        # Try to register failure if document_id exists
        if document_id:
            try:
                await service.register_ingestion_failure(
                    document_id=document_id,
                    failure_reason=str(e),
                    processing_time_ms=processing_time
                )
            except:
                pass
        
        return {
            "status": "failed",
            "chunks": 0,
            "message": str(e),
            "processing_time_ms": processing_time
        }


def create_text_chunks(text: str, source: str, chunk_size: int = 200, overlap: int = 50) -> list:
    """
    Chunk plain text using character-based splitting.
    Wrapper around existing chunking logic for non-PDF files.
    
    Args:
        text: Text content to chunk
        source: Source identifier
        chunk_size: Size of chunks in characters
        overlap: Overlap between chunks
        
    Returns:
        List of chunk dictionaries with text and metadata
    """
    if not text or not text.strip():
        return []
    
    chunks = []
    text_length = len(text)
    start = 0
    chunk_index = 0
    
    while start < text_length:
        # Calculate end position
        end = min(start + chunk_size, text_length)
        
        # Extract chunk
        chunk_text = text[start:end]
        
        # Skip empty chunks
        if chunk_text.strip():
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "source": source,
                    "chunk_index": chunk_index,
                    "start_char": start,
                    "end_char": end,
                    "chunk_length": len(chunk_text)
                }
            })
            chunk_index += 1
        
        # Move start position (accounting for overlap)
        start = end - overlap if end < text_length else text_length
    
    return chunks
