from typing import Optional, List, Dict, Tuple, Any
import time
import re
import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path
from app.core.logging import setup_logger
from app.core.config import settings
from app.core.cache import get_embedding_cache, generate_cache_key
from app.utils.graceful_response import graceful_fallback, success_message, add_graceful_context

# Initialize logger
logger = setup_logger("INFO")

# Global variables for model and client
_embedding_model: Optional[SentenceTransformer] = None
_chroma_client: Optional[chromadb.PersistentClient] = None
_collection = None

# Confidence threshold for retrieval
CONFIDENCE_THRESHOLD = settings.CONFIDENCE_THRESHOLD

# Important keywords for keyword boosting
IMPORTANT_KEYWORDS = [
    "role", "position", "title", "name", "experience", "job",
    "education", "skills", "certification", "company", "project",
    "responsibility", "achievement", "award", "degree", "university",
    "phone", "email", "address", "contact", "website", "linkedin"
]


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
    Get the Chroma collection for RAG documents.
    
    Returns:
        The Chroma collection
    
    Raises:
        ValueError: If the collection doesn't exist
    """
    global _chroma_client, _collection
    
    if _collection is None:
        vector_store_path = get_vector_store_path()
        
        if not vector_store_path.exists():
            raise ValueError(
                "Vector store not found. Please ingest documents first using /rag/ingest"
            )
        
        logger.info(f"Connecting to Chroma DB at {vector_store_path}")
        _chroma_client = chromadb.PersistentClient(path=str(vector_store_path))
        
        try:
            _collection = _chroma_client.get_collection(name="rag_documents")
            logger.info("Connected to Chroma collection")
        except Exception:
            raise ValueError(
                "RAG collection not found. Please ingest documents first using /rag/ingest"
            )
    
    return _collection


def extract_important_keywords(query: str) -> List[str]:
    """
    Extract important keywords from query for boosted retrieval.
    
    Args:
        query: The search query
    
    Returns:
        List of important keywords found in the query
    """
    query_lower = query.lower()
    found_keywords = []
    
    for keyword in IMPORTANT_KEYWORDS:
        if keyword in query_lower:
            found_keywords.append(keyword)
    
    # Also extract capitalized words (likely names/titles)
    capitalized_words = re.findall(r'\b[A-Z][a-z]+\b', query)
    found_keywords.extend(capitalized_words)
    
    return list(set(found_keywords))  # Remove duplicates


def build_boosted_query(original_query: str, keywords: List[str]) -> str:
    """
    Build a keyword-boosted query by emphasizing important terms.
    
    Args:
        original_query: The original search query
        keywords: List of important keywords to boost
    
    Returns:
        Boosted query string
    """
    if not keywords:
        return original_query
    
    # Emphasize keywords by repeating them
    boosted = f"{original_query} {' '.join(keywords * 2)}"
    return boosted


def search(query: str, top_k: int = 5, document_id: Optional[str] = None) -> Tuple[list, dict]:
    """
    Search for relevant documents using vector similarity with automatic fallback.
    
    Performs a two-pass retrieval strategy:
    1. Primary search with standard parameters
    2. If confidence is low, automatically runs fallback search with:
       - Higher top_k (expanded search)
       - Keyword-boosted query
    
    Args:
        query: Search query string
        top_k: Number of top results to return
        document_id: Optional document ID to filter results (only return chunks from this document)
    
    Returns:
        Tuple of (results, telemetry_meta) where telemetry_meta contains:
        - confidence_top: Top similarity score
        - confidence_threshold: Threshold used
        - confidence_decision: accepted | fallback_retry | rejected
        - retrieval_pass: primary | fallback
        - top_k_scores: Array of top scores
        - latency_ms_retrieval: Retrieval latency
        - cache_hit: Whether embedding was cached
        - document_id_filter: Document ID used for filtering (if any)
    
    Raises:
        ValueError: If the collection doesn't exist
    """
    start_time = time.time()
    
    # Initialize telemetry
    telemetry = {
        "confidence_top": 0.0,
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "confidence_decision": "rejected",
        "retrieval_pass": "primary",
        "top_k_scores": [],
        "latency_ms_retrieval": 0,
        "cache_hit": False,
        "document_id_filter": document_id
    }
    
    try:
        logger.info(f"Searching for query: '{query[:50]}...' (top {top_k})")
        
        # Get embedding model and collection
        model = get_embedding_model()
        collection = get_chroma_collection()
        
        # ========================================
        # EMBEDDING WITH CACHE
        # ========================================
        cache_key = generate_cache_key(query, "embedding")
        embedding_cache = get_embedding_cache() if settings.CACHE_ENABLED else None
        
        query_embedding = None
        if embedding_cache:
            query_embedding = embedding_cache.get(cache_key)
            if query_embedding:
                telemetry["cache_hit"] = True
                logger.debug(f"cache_status=hit type=embedding")
        
        if query_embedding is None:
            query_embedding = model.encode([query])[0].tolist()
            if embedding_cache:
                embedding_cache.set(cache_key, query_embedding)
                logger.debug(f"cache_status=miss type=embedding")
        
        # ========================================
        # PRIMARY SEARCH
        # ========================================
        # Build where clause for document_id filtering
        where_clause = None
        if document_id:
            # Filter by document_id metadata field
            where_clause = {"document_id": {"$eq": document_id}}
            logger.info(f"Filtering search by document_id: {document_id}")
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k * 3 if document_id else top_k,  # Get more if filtering
            include=["documents", "distances", "metadatas"],
            where=where_clause
        )
        
        # Format primary results
        primary_results = _format_results(results)
        
        if not primary_results:
            logger.warning("Primary search returned no results")
            telemetry["latency_ms_retrieval"] = int((time.time() - start_time) * 1000)
            telemetry["confidence_decision"] = "rejected"
            return [], telemetry
        
        # Check confidence of top result
        primary_top_score = primary_results[0].get("score", 0)
        telemetry["confidence_top"] = primary_top_score
        telemetry["top_k_scores"] = [r.get("score", 0) for r in primary_results]
        
        logger.info(f"Primary search top score: {primary_top_score:.4f}")
        
        # If confidence is high, return primary results
        if primary_top_score >= CONFIDENCE_THRESHOLD:
            logger.info(f"High confidence detected (mode=primary_search, score={primary_top_score:.4f})")
            telemetry["confidence_decision"] = "accepted"
            telemetry["retrieval_pass"] = "primary"
            telemetry["latency_ms_retrieval"] = int((time.time() - start_time) * 1000)
            logger.info(f"routing_decision=primary_accepted confidence={primary_top_score:.4f}")
            return primary_results, telemetry
        
        # ========================================
        # SECOND-PASS FALLBACK RETRIEVAL
        # ========================================
        logger.info(f"Low confidence ({primary_top_score:.4f} < {CONFIDENCE_THRESHOLD}), triggering fallback retrieval")
        logger.info(f"fallback_mode=triggered primary_score={primary_top_score:.4f}")
        
        # Extract important keywords for boosting
        keywords = extract_important_keywords(query)
        logger.info(f"Extracted keywords for boosting: {keywords}")
        
        # Build boosted query
        boosted_query = build_boosted_query(query, keywords)
        
        # Expand search parameters
        fallback_top_k = max(top_k * 2, 10)  # At least 10 results
        logger.info(f"Fallback search with expanded top_k={fallback_top_k} and keyword boosting")
        
        # Generate embedding for boosted query
        boosted_embedding = model.encode([boosted_query])[0].tolist()
        
        # Perform fallback search
        fallback_results_raw = collection.query(
            query_embeddings=[boosted_embedding],
            n_results=fallback_top_k,
            include=["documents", "distances", "metadatas"],
            where=where_clause  # Apply same document_id filter
        )
        
        # Format fallback results
        fallback_results = _format_results(fallback_results_raw)
        
        if not fallback_results:
            logger.warning("Fallback search returned no results, using primary results")
            telemetry["confidence_decision"] = "fallback_retry"
            telemetry["retrieval_pass"] = "primary"
            telemetry["latency_ms_retrieval"] = int((time.time() - start_time) * 1000)
            return primary_results, telemetry
        
        fallback_top_score = fallback_results[0].get("score", 0)
        logger.info(f"Fallback search top score: {fallback_top_score:.4f}")
        
        # Compare and return better results
        if fallback_top_score > primary_top_score:
            logger.info(
                f"Fallback improved confidence "
                f"(mode=second_pass_retry, primary_score={primary_top_score:.4f}, "
                f"fallback_score={fallback_top_score:.4f})"
            )
            telemetry["confidence_top"] = fallback_top_score
            telemetry["confidence_decision"] = "fallback_retry" if fallback_top_score >= CONFIDENCE_THRESHOLD else "accepted"
            telemetry["retrieval_pass"] = "fallback"
            telemetry["top_k_scores"] = [r.get("score", 0) for r in fallback_results[:top_k]]
            telemetry["latency_ms_retrieval"] = int((time.time() - start_time) * 1000)
            logger.info(f"routing_decision=fallback_accepted confidence={fallback_top_score:.4f}")
            return fallback_results[:top_k], telemetry
        else:
            logger.info(
                f"Primary search was better "
                f"(mode=primary_search_retained, primary_score={primary_top_score:.4f}, "
                f"fallback_score={fallback_top_score:.4f})"
            )
            telemetry["confidence_decision"] = "fallback_retry"
            telemetry["retrieval_pass"] = "primary"
            telemetry["latency_ms_retrieval"] = int((time.time() - start_time) * 1000)
            logger.info(f"routing_decision=primary_retained confidence={primary_top_score:.4f}")
            return primary_results, telemetry
        
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        telemetry["latency_ms_retrieval"] = int((time.time() - start_time) * 1000)
        raise RuntimeError(f"Search failed: {str(e)}")


def _format_results(results: Dict) -> List[Dict]:
    """
    Format raw Chroma results into standardized format.
    
    Args:
        results: Raw results from Chroma query
    
    Returns:
        List of formatted results with chunks, scores, metadata, and IDs
    """
    formatted_results = []
    
    if results.get('documents') and len(results['documents']) > 0:
        documents = results['documents'][0]
        distances = results.get('distances', [[]])[0]
        metadatas = results.get('metadatas', [[]])[0]
        ids = results.get('ids', [[]])[0]  # Get IDs
        
        for i, doc in enumerate(documents):
            # Convert distance to similarity score (lower distance = higher similarity)
            # Normalize to 0-1 range where 1 is perfect match
            distance = distances[i] if i < len(distances) else 1.0
            score = max(0.0, 1.0 - (distance / 2.0))  # Simple normalization
            
            result = {
                "chunk": doc,
                "score": round(score, 4)
            }
            
            # Add ID if available
            if i < len(ids):
                result["id"] = ids[i]
            
            # Add metadata if available
            if i < len(metadatas) and metadatas[i]:
                result["metadata"] = metadatas[i]
            
            formatted_results.append(result)
    
    return formatted_results


def clear_test_documents(source_pattern: str = "test") -> Dict[str, Any]:
    """
    Delete test documents from the vector store to ensure clean test runs.
    
    Args:
        source_pattern: Pattern to match in source field (default: "test")
    
    Returns:
        Dictionary with deletion results:
        - deleted_count: Number of chunks deleted
        - status: "success" or "error"
        - message: Status message
    """
    logger = setup_logger()
    
    try:
        collection = get_chroma_collection()
        
        # Get all documents
        all_docs = collection.get()
        
        if not all_docs or not all_docs.get('ids'):
            return {
                "deleted_count": 0,
                "status": "success",
                "message": "No documents found in collection"
            }
        
        # Find IDs matching the pattern
        ids_to_delete = []
        metadatas = all_docs.get('metadatas', [])
        all_ids = all_docs.get('ids', [])
        
        for i, metadata in enumerate(metadatas):
            if metadata and isinstance(metadata, dict):
                source = metadata.get('source', '')
                if source_pattern in source:
                    ids_to_delete.append(all_ids[i])
        
        # Delete matching documents
        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            logger.info(f"Deleted {len(ids_to_delete)} test documents from vector store")
            return {
                "deleted_count": len(ids_to_delete),
                "status": "success",
                "message": f"Deleted {len(ids_to_delete)} documents matching pattern '{source_pattern}'"
            }
        else:
            return {
                "deleted_count": 0,
                "status": "success",
                "message": f"No documents found matching pattern '{source_pattern}'"
            }
            
    except Exception as e:
        logger.error(f"Failed to clear test documents: {str(e)}")
        return {
            "deleted_count": 0,
            "status": "error",
            "message": f"Error: {str(e)}"
        }


def search_with_graceful_response(
    query: str,
    top_k: int = 5,
    document_id: Optional[str] = None
) -> Tuple[list, dict]:
    """
    Enhanced search wrapper that adds graceful user-friendly messaging.
    
    Wraps the standard search() function and adds human-friendly messages
    for success, degradation, and failure cases while preserving all
    technical metadata and telemetry.
    
    Args:
        query: Search query string
        top_k: Number of top results to return
        document_id: Optional document ID filter
        
    Returns:
        Tuple of (results, enhanced_telemetry) where enhanced_telemetry includes:
        - All standard telemetry from search()
        - graceful_message: Human-friendly message (or None for full success)
        - degradation_level: none | mild | fallback | degraded | failed
        - user_action_hint: Suggestion for user action (or None)
        - fallback_reason: Technical reason if degraded (for debugging)
    """
    try:
        results, telemetry = search(query, top_k, document_id)
        
        # No results found
        if not results:
            graceful_data = graceful_fallback(
                "rag_no_results",
                reason="search_returned_empty",
                meta=telemetry
            )
            return results, graceful_data
        
        # Check confidence level
        confidence_top = telemetry.get("confidence_top", 0.0)
        confidence_threshold = telemetry.get("confidence_threshold", CONFIDENCE_THRESHOLD)
        
        # Low confidence case
        if confidence_top < confidence_threshold:
            graceful_data = graceful_fallback(
                "rag_low_confidence",
                reason=f"max_similarity={confidence_top:.3f} < threshold={confidence_threshold}",
                meta=telemetry
            )
            return results, graceful_data
        
        # Success - high confidence
        graceful_data = success_message("rag_search", telemetry)
        return results, graceful_data
        
    except ValueError as e:
        # Collection doesn't exist - no documents ingested
        if "not found" in str(e).lower() or "ingest documents" in str(e).lower():
            graceful_data = graceful_fallback(
                "rag_no_documents",
                reason="vector_store_empty",
                meta={"error": str(e)}
            )
            return [], graceful_data
        raise
        
    except Exception as e:
        # Unexpected errors
        logger.error(f"Search failed with error: {str(e)}")
        raise


