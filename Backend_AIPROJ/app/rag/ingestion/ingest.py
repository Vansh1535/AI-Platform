from pathlib import Path
from typing import Optional
import time
import chromadb
from sentence_transformers import SentenceTransformer
from app.core.logging import setup_logger
from app.docqa.pipeline.process_pdf import process_pdf
from app.rag.ingestion.chunking import chunk_pages
from app.rag.ingestion.document_registry import get_registry
from app.rag.ingestion.validators import validate_document_for_ingestion, ValidationError
from app.rag.ingestion.checksum import compute_file_checksum, check_duplicate_policy, generate_document_id

# Initialize logger
logger = setup_logger("INFO")

# Global variables for model and client
_embedding_model: Optional[SentenceTransformer] = None
_chroma_client: Optional[chromadb.PersistentClient] = None
_collection = None


def get_vector_store_path() -> Path:
    """Get the path to the vector store directory."""
    return Path(__file__).parent.parent.parent.parent / "data" / "vector_store"


def get_embedding_model() -> SentenceTransformer:
    """
    Load and cache the sentence transformer model.
    
    Returns:
        The embedding model
    """
    global _embedding_model
    
    if _embedding_model is None:
        logger.info("Loading sentence transformer model: all-MiniLM-L6-v2")
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Embedding model loaded successfully")
    
    return _embedding_model


def get_chroma_collection():
    """
    Get or create the Chroma collection for RAG documents.
    
    Returns:
        The Chroma collection
    """
    global _chroma_client, _collection
    
    if _collection is None:
        vector_store_path = get_vector_store_path()
        vector_store_path.mkdir(exist_ok=True)
        
        logger.info(f"Initializing Chroma DB at {vector_store_path}")
        _chroma_client = chromadb.PersistentClient(path=str(vector_store_path))
        
        _collection = _chroma_client.get_or_create_collection(
            name="rag_documents",
            metadata={"description": "RAG document embeddings"}
        )
        logger.info("Chroma collection initialized")
    
    return _collection


def chunk_text(text: str, chunk_size: int = 200, overlap: int = 50) -> list[str]:
    """
    Split text into fixed-size chunks with overlap.
    
    Args:
        text: The text to chunk
        chunk_size: Size of each chunk in characters
        overlap: Number of overlapping characters between chunks
    
    Returns:
        List of text chunks
    """
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():  # Only add non-empty chunks
            chunks.append(chunk.strip())
        start += chunk_size - overlap
    
    return chunks


def ingest_document(doc: str) -> dict:
    """
    Ingest a document by chunking, embedding, and storing in Chroma.
    
    Args:
        doc: Document text to ingest
    
    Returns:
        Ingestion result with status and chunk count
    """
    try:
        logger.info(f"Starting document ingestion - Length: {len(doc)} chars")
        
        # Chunk the document
        chunks = chunk_text(doc)
        num_chunks = len(chunks)
        logger.info(f"Document split into {num_chunks} chunks")
        
        if num_chunks == 0:
            return {"status": "failed", "chunks": 0, "message": "Document is empty"}
        
        # Get embedding model and collection
        model = get_embedding_model()
        collection = get_chroma_collection()
        
        # Generate embeddings
        logger.info("Generating embeddings...")
        embeddings = model.encode(chunks).tolist()
        
        # Generate unique IDs for chunks
        import uuid
        doc_id = str(uuid.uuid4())[:8]
        ids = [f"{doc_id}_chunk_{i}" for i in range(num_chunks)]
        
        # Store in Chroma
        collection.add(
            embeddings=embeddings,
            documents=chunks,
            ids=ids,
            metadatas=[{"chunk_index": i, "doc_id": doc_id} for i in range(num_chunks)]
        )
        
        logger.info(f"Successfully ingested {num_chunks} chunks into vector store")
        
        return {
            "status": "ingested",
            "chunks": num_chunks
        }
        
    except Exception as e:
        logger.error(f"Document ingestion failed: {str(e)}")
        return {
            "status": "failed",
            "chunks": 0,
            "message": str(e)
        }


def ingest_pdf(
    file_path: str, 
    source: str,
    chunk_size: int = 200,
    overlap: int = 50,
    exists_policy: str = "skip"
) -> dict:
    """
    Ingest a PDF document with full validation, metadata tracking, and audit logging.
    
    Args:
        file_path: Path to the PDF file
        source: Source identifier for the document
        chunk_size: Size of text chunks (default: 200)
        overlap: Overlap between chunks (default: 50)
        exists_policy: Policy for existing documents - skip/overwrite/version_as_new (default: skip)
    
    Returns:
        Ingestion result with status, chunk count, page count, and document_id
    """
    start_time = time.time()
    registry = get_registry()
    
    try:
        logger.info(f"Starting PDF ingestion pipeline - File: {file_path}, Source: {source}, Policy: {exists_policy}")
        
        # Step 1: Validation Pipeline
        logger.info("Step 1: Validating document...")
        try:
            validation_result = validate_document_for_ingestion(
                file_path=file_path,
                chunk_size=chunk_size,
                overlap=overlap,
                tokenizer_name="character"
            )
        except ValidationError as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"Validation failed: {e.message}")
            return {
                "status": "failed",
                "chunks": 0,
                "pages": 0,
                "message": e.message,
                "error": e.to_dict(),
                "processing_time_ms": processing_time
            }
        
        # Step 2: Compute Checksum
        logger.info("Step 2: Computing file checksum...")
        checksum = compute_file_checksum(file_path)
        
        # Step 3: Check for Duplicates
        logger.info("Step 3: Checking duplicate policy...")
        duplicate_check = check_duplicate_policy(checksum, registry, exists_policy)
        
        if duplicate_check["action"] == "skip":
            processing_time = int((time.time() - start_time) * 1000)
            existing_doc = duplicate_check["existing_docs"][0]
            logger.info(f"Skipping duplicate document: {existing_doc['document_id']}")
            return {
                "status": "skipped",
                "reason": "duplicate_exists",
                "document_id": existing_doc["document_id"],
                "chunks": existing_doc.get("chunk_count", 0),
                "pages": existing_doc.get("page_count", 0),
                "processing_time_ms": processing_time,
                "existing_document": existing_doc
            }
        
        # Step 4: Generate Document ID
        version = duplicate_check.get("version", 1)
        document_id = generate_document_id(
            validation_result["filename"],
            checksum,
            version
        )
        
        # Step 5: Register Ingestion Start
        logger.info(f"Step 5: Registering ingestion start for document: {document_id}")
        registry.register_ingestion_start(
            document_id=document_id,
            filename=validation_result["filename"],
            file_type="pdf",
            file_size_bytes=validation_result["file_size_bytes"],
            checksum_hash=checksum,
            source_path=file_path,
            chunk_size=chunk_size,
            overlap=overlap,
            tokenizer_name="character",
            exists_policy=exists_policy
        )
        
        # Step 6: Extract text from PDF
        logger.info("Step 6: Extracting text from PDF...")
        pages_data = process_pdf(file_path)
        num_pages = len(pages_data)
        logger.info(f"Extracted {num_pages} pages from PDF")
        
        if num_pages == 0:
            processing_time = int((time.time() - start_time) * 1000)
            registry.register_ingestion_failure(
                document_id=document_id,
                failure_reason="No text extracted from PDF",
                processing_time_ms=processing_time
            )
            return {
                "status": "failed",
                "document_id": document_id,
                "chunks": 0,
                "pages": 0,
                "message": "No text extracted from PDF",
                "processing_time_ms": processing_time
            }
        
        # Step 7: Chunk the pages
        logger.info("Step 7: Chunking pages...")
        chunks_data = chunk_pages(pages_data, source)
        num_chunks = len(chunks_data)
        logger.info(f"Created {num_chunks} chunks from {num_pages} pages")
        
        if num_chunks == 0:
            processing_time = int((time.time() - start_time) * 1000)
            registry.register_ingestion_failure(
                document_id=document_id,
                failure_reason="No chunks created from PDF",
                processing_time_ms=processing_time
            )
            return {
                "status": "failed",
                "document_id": document_id,
                "chunks": 0,
                "pages": num_pages,
                "message": "No chunks created from PDF",
                "processing_time_ms": processing_time
            }
        
        # Step 8: Generate embeddings and store
        logger.info("Step 8: Generating embeddings...")
        model = get_embedding_model()
        collection = get_chroma_collection()
        
        chunk_texts = [chunk["text"] for chunk in chunks_data]
        chunk_metadatas = [chunk["metadata"] for chunk in chunks_data]
        
        embeddings = model.encode(chunk_texts).tolist()
        
        # Generate unique IDs for chunks
        ids = [f"{document_id}_chunk_{i}" for i in range(num_chunks)]
        
        # Store in Chroma with full metadata
        logger.info("Step 9: Storing in vector database...")
        collection.add(
            embeddings=embeddings,
            documents=chunk_texts,
            ids=ids,
            metadatas=chunk_metadatas
        )
        
        # Step 10: Estimate tokens (rough approximation: 1 token ≈ 4 chars)
        total_chars = sum(len(text) for text in chunk_texts)
        token_estimate = total_chars // 4
        
        # Step 11: Register success
        processing_time = int((time.time() - start_time) * 1000)
        logger.info(f"Step 11: Registering ingestion success...")
        registry.register_ingestion_success(
            document_id=document_id,
            page_count=num_pages,
            chunk_count=num_chunks,
            token_estimate=token_estimate,
            processing_time_ms=processing_time
        )
        
        logger.info(
            f"PDF ingestion complete: {document_id} - "
            f"{num_chunks} chunks from {num_pages} pages in {processing_time}ms"
        )
        
        return {
            "status": "success",
            "document_id": document_id,
            "chunks": num_chunks,
            "pages": num_pages,
            "token_estimate": token_estimate,
            "processing_time_ms": processing_time,
            "checksum": checksum,
            "version": version
        }
        
    except ValidationError as e:
        processing_time = int((time.time() - start_time) * 1000)
        logger.error(f"Validation error: {e.message}")
        return {
            "status": "failed",
            "chunks": 0,
            "pages": 0,
            "message": e.message,
            "error": e.to_dict(),
            "processing_time_ms": processing_time
        }
    
    except FileNotFoundError as e:
        processing_time = int((time.time() - start_time) * 1000)
        logger.error(f"PDF file not found: {str(e)}")
        return {
            "status": "failed",
            "chunks": 0,
            "pages": 0,
            "message": str(e),
            "processing_time_ms": processing_time
        }
    
    except Exception as e:
        processing_time = int((time.time() - start_time) * 1000)
        logger.error(f"PDF ingestion failed: {str(e)}")
        
        # Try to register failure if document_id exists
        try:
            if 'document_id' in locals():
                registry.register_ingestion_failure(
                    document_id=document_id,
                    failure_reason=str(e),
                    processing_time_ms=processing_time
                )
        except:
            pass
        
        return {
            "status": "failed",
            "chunks": 0,
            "pages": 0,
            "message": str(e),
            "processing_time_ms": processing_time
        }
