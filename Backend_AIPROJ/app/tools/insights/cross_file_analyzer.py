"""
Cross-File Semantic Intelligence Module

Provides document-level semantic analysis across multiple files:
- Compute embeddings for document summaries
- Perform cross-file similarity clustering
- Detect shared themes and overlapping concepts
- Generate cluster metadata with evidence

Key Features:
- Document-level clustering (not phrase-level)
- Cosine similarity-based grouping
- Auto-generated theme labels
- Confidence scoring per cluster
- Evidence snippets with source references
- Graceful fallback for edge cases

Design Principles:
- Deterministic extractive mode by default
- LLM synthesis only when mode="llm_synthesis"
- Never crash - always return structured output
- Observability-first with comprehensive telemetry
"""

import logging
import time
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)

# Clustering configuration
DOC_SIMILARITY_THRESHOLD = 0.45  # Documents must be at least 45% similar to cluster
MIN_DOCS_FOR_CLUSTERING = 2  # Need at least 2 docs to form a cluster
MIN_CLUSTER_SIZE = 2  # Cluster must have at least 2 members
WEAK_SIGNAL_THRESHOLD = 0.30  # Below this = weak signals
EVIDENCE_SNIPPET_LENGTH = 150  # Character length for evidence excerpts


def get_embedding_function():
    """
    Get the embedding function for document-level clustering.
    Reuses Phase A embedding infrastructure.
    
    Returns:
        Embedding function or None if unavailable
    """
    try:
        from app.rag.retrieval.search import get_embedding_model
        model = get_embedding_model()
        
        def embed_texts(texts: List[str]) -> List[List[float]]:
            """Embed list of texts and return as list of lists."""
            embeddings = model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        
        # Test embedding function
        test_result = embed_texts(["test"])
        if test_result and len(test_result) > 0:
            logger.debug("Embedding function initialized successfully")
            return embed_texts
        else:
            logger.warning("Embedding function test failed - returned invalid result")
            return None
            
    except ImportError as e:
        logger.warning(f"Cannot import embedding model: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error initializing embedding function: {str(e)}")
        return None


def compute_cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Similarity score [0, 1]
    """
    try:
        # Normalize vectors
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = np.dot(vec1, vec2) / (norm1 * norm2)
        
        # Ensure in valid range [0, 1]
        return float(max(0.0, min(1.0, similarity)))
        
    except Exception as e:
        logger.error(f"Error computing cosine similarity: {str(e)}")
        return 0.0


def extract_theme_label_from_summary(summary_text: str, max_words: int = 4) -> str:
    """
    Extract a short theme label from document summary.
    Uses extractive approach - picks most representative phrase.
    
    Args:
        summary_text: The document summary text
        max_words: Maximum words in label
        
    Returns:
        Short theme label (e.g., "API Security", "Database Migration")
    """
    import re
    
    # Clean text
    text = re.sub(r'Document Summary.*?\n', '', summary_text, flags=re.IGNORECASE)
    text = re.sub(r'Key Points:?\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^\d+\.\s*', '', text, flags=re.MULTILINE)
    
    # Extract capitalized phrases (likely key topics)
    phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\b', text)
    
    if phrases:
        # Return most common phrase
        phrase_counts = Counter(phrases)
        most_common = phrase_counts.most_common(1)[0][0]
        words = most_common.split()
        return ' '.join(words[:max_words])
    
    # Fallback: extract first capitalized words
    words = text.split()
    cap_words = [w for w in words if w and w[0].isupper() and len(w) > 3]
    
    if cap_words:
        return ' '.join(cap_words[:max_words])
    
    # Last resort: generic label
    return "General Topic"


def generate_cluster_theme_label(
    cluster_members: List[Dict[str, Any]],
    mode: str = "extractive"
) -> str:
    """
    Generate theme label for a document cluster.
    
    Args:
        cluster_members: List of document summaries in cluster
        mode: "extractive" (default) or "llm_synthesis"
        
    Returns:
        Theme label for the cluster
    """
    if mode == "llm_synthesis":
        # LLM-based synthesis (not implemented yet - placeholder)
        logger.info("LLM synthesis mode requested but not yet implemented, using extractive")
        mode = "extractive"
    
    # Extractive mode: Find common themes across summaries
    all_phrases = []
    for member in cluster_members:
        summary_text = member.get('summary', '')
        phrase = extract_theme_label_from_summary(summary_text)
        all_phrases.append(phrase)
    
    # Find most common phrase
    phrase_counts = Counter(all_phrases)
    
    if phrase_counts:
        # Use most common theme
        most_common_phrase, count = phrase_counts.most_common(1)[0]
        
        # If all documents share same theme, use it
        if count >= len(cluster_members) * 0.5:  # At least 50% share
            return most_common_phrase
    
    # Fallback: combine unique themes
    unique_phrases = list(set(all_phrases))
    if len(unique_phrases) == 1:
        return unique_phrases[0]
    elif len(unique_phrases) <= 3:
        return " & ".join(unique_phrases[:2])  # Combine top 2
    else:
        return "Mixed Topics"


def extract_evidence_snippets(
    cluster_members: List[Dict[str, Any]],
    max_snippets: int = 3
) -> List[Dict[str, Any]]:
    """
    Extract evidence snippets from cluster member documents.
    
    Args:
        cluster_members: List of document summaries in cluster
        max_snippets: Maximum snippets to return
        
    Returns:
        List of evidence dicts with document_id and snippet
    """
    evidence = []
    
    for member in cluster_members[:max_snippets]:
        doc_id = member.get('document_id', 'unknown')
        summary = member.get('summary', '')
        
        # Extract first meaningful sentence as snippet
        sentences = [s.strip() for s in summary.split('.') if len(s.strip()) > 20]
        
        if sentences:
            snippet = sentences[0][:EVIDENCE_SNIPPET_LENGTH]
            if len(sentences[0]) > EVIDENCE_SNIPPET_LENGTH:
                snippet += "..."
        else:
            # Fallback to truncated summary
            snippet = summary[:EVIDENCE_SNIPPET_LENGTH]
            if len(summary) > EVIDENCE_SNIPPET_LENGTH:
                snippet += "..."
        
        evidence.append({
            "document_id": doc_id,
            "snippet": snippet,
            "chunks_used": member.get('chunks_used', 0)
        })
    
    return evidence


def cluster_documents_by_similarity(
    summaries: List[Dict[str, Any]],
    embedding_function,
    similarity_threshold: float = DOC_SIMILARITY_THRESHOLD,
    mode: str = "extractive"
) -> List[Dict[str, Any]]:
    """
    Cluster documents based on summary semantic similarity.
    
    Uses greedy agglomerative approach:
    1. Compute embeddings for all document summaries
    2. For each document, find similar documents (cosine similarity)
    3. Group into clusters with confidence scores
    
    Args:
        summaries: List of per-document summary dicts
        embedding_function: Function to generate embeddings
        similarity_threshold: Minimum similarity to join cluster
        mode: "extractive" (default) or "llm_synthesis"
        
    Returns:
        List of cluster dicts with metadata
    """
    if not summaries or not embedding_function:
        logger.warning("Cannot cluster - no summaries or embedding function")
        return []
    
    try:
        # Extract summary texts
        summary_texts = [s.get('summary', '') for s in summaries]
        
        if not any(summary_texts):
            logger.warning("All summaries are empty")
            return []
        
        # Generate embeddings for all summaries
        logger.info(f"Generating embeddings for {len(summary_texts)} document summaries...")
        start_time = time.time()
        embeddings = embedding_function(summary_texts)
        embed_time = int((time.time() - start_time) * 1000)
        logger.debug(f"Embeddings generated in {embed_time}ms")
        
        if not embeddings or len(embeddings) != len(summary_texts):
            logger.error(f"Embedding generation failed - expected {len(summary_texts)}, got {len(embeddings) if embeddings else 0}")
            return []
        
        # Convert to numpy arrays
        embeddings = [np.array(emb) for emb in embeddings]
        
        # Initialize clustering state
        clusters = []
        used_indices = set()
        
        # Greedy clustering: for each document, find all similar documents
        for i, doc in enumerate(summaries):
            if i in used_indices:
                continue
            
            # Start new cluster with this document
            cluster_members = [summaries[i]]
            cluster_indices = [i]
            similarities = []
            
            # Find similar documents
            for j in range(i + 1, len(summaries)):
                if j in used_indices:
                    continue
                
                similarity = compute_cosine_similarity(embeddings[i], embeddings[j])
                
                if similarity >= similarity_threshold:
                    cluster_members.append(summaries[j])
                    cluster_indices.append(j)
                    similarities.append(similarity)
                    used_indices.add(j)
            
            # Mark primary document as used
            used_indices.add(i)
            
            # Calculate cluster confidence (average pairwise similarity)
            if similarities:
                avg_similarity = sum(similarities) / len(similarities)
            else:
                # Single-member cluster - no internal similarity
                avg_similarity = 1.0 if len(cluster_members) == 1 else 0.0
            
            # Only include multi-member clusters
            if len(cluster_members) >= MIN_CLUSTER_SIZE:
                # Generate theme label
                theme_label = generate_cluster_theme_label(cluster_members, mode)
                
                # Extract evidence
                evidence = extract_evidence_snippets(cluster_members)
                
                # Get document IDs
                member_docs = [m.get('document_id', 'unknown') for m in cluster_members]
                
                cluster = {
                    "theme_label": theme_label,
                    "member_documents": member_docs,
                    "member_count": len(cluster_members),
                    "confidence_score": round(avg_similarity, 3),
                    "evidence_snippets": evidence,
                    "cluster_type": "cross_file_semantic"
                }
                
                clusters.append(cluster)
        
        # Sort by confidence and size
        clusters.sort(key=lambda x: (x['confidence_score'], x['member_count']), reverse=True)
        
        logger.info(f"Created {len(clusters)} document-level clusters from {len(summaries)} documents")
        
        return clusters
        
    except Exception as e:
        logger.error(f"Error during document clustering: {str(e)}")
        return []


def analyze_cross_file_semantics(
    per_document_summaries: List[Dict[str, Any]],
    mode: str = "extractive"
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Perform cross-file semantic analysis on document summaries.
    
    Main entry point for cross-file intelligence.
    
    Args:
        per_document_summaries: List of per-document summary dicts
        mode: "extractive" (default) or "llm_synthesis"
        
    Returns:
        Tuple of (result_dict, telemetry_dict)
        
    Result structure:
        {
            "semantic_clusters": [{
                "theme_label": str,
                "member_documents": [doc_ids],
                "member_count": int,
                "confidence_score": float,
                "evidence_snippets": [{document_id, snippet, relevance}],
                "cluster_type": "cross_file_semantic"
            }],
            "cluster_confidence": float,
            "cross_file_overlap_detected": bool,
            "shared_themes": [...],
            "processing_mode": str
        }
        
    Telemetry structure (with observability fields):
        {
            "latency_ms_total": int,
            "clustering_used": bool,
            "llm_used": bool,
            "fallback_triggered": bool,
            "degradation_level": "none"|"degraded"|"fallback",
            "graceful_message": str or None,
            "cluster_count": int,
            "avg_cluster_confidence": float,
            "documents_clustered": int,
            "documents_unclustered": int,
            "weak_signals_detected": bool
        }
    """
    start_time = time.time()
    
    # Initialize result and telemetry structures with observability fields
    result = {
        "semantic_clusters": [],
        "cluster_confidence": None,
        "cross_file_overlap_detected": False,
        "shared_themes": [],
        "processing_mode": "none"
    }
    
    telemetry = {
        "latency_ms_total": 0,
        "clustering_used": False,
        "llm_used": False,
        "fallback_triggered": False,
        "degradation_level": "none",
        "graceful_message": None,
        "cluster_count": 0,
        "avg_cluster_confidence": 0.0,
        "documents_clustered": 0,
        "documents_unclustered": len(per_document_summaries) if per_document_summaries else 0,
        "weak_signals_detected": False
    }
    
    try:
        # Validation: Check minimum documents
        if len(per_document_summaries) < MIN_DOCS_FOR_CLUSTERING:
            logger.info(f"Too few documents for cross-file analysis: {len(per_document_summaries)} < {MIN_DOCS_FOR_CLUSTERING}")
            telemetry["fallback_triggered"] = True
            telemetry["degradation_level"] = "fallback"
            telemetry["graceful_message"] = f"Need at least {MIN_DOCS_FOR_CLUSTERING} documents for cross-file analysis."
            telemetry["latency_ms"] = int((time.time() - start_time) * 1000)
            return result, telemetry
        
        # Get embedding function
        embedding_function = get_embedding_function()
        
        if not embedding_function:
            logger.warning("Embeddings unavailable - cannot perform cross-file analysis")
            telemetry["fallback_reason"] = "embeddings_unavailable"
            telemetry["latency_ms"] = int((time.time() - start_time) * 1000)
            return result, telemetry
        
        # Perform document-level clustering
        logger.info(f"Starting cross-file semantic clustering of {len(per_document_summaries)} documents...")
        clusters = cluster_documents_by_similarity(
            per_document_summaries,
            embedding_function,
            similarity_threshold=DOC_SIMILARITY_THRESHOLD,
            mode=mode
        )
        
        if not clusters:
            logger.info("No clusters formed - documents may be too dissimilar")
            telemetry["fallback_reason"] = "no_clusters_formed"
            telemetry["latency_ms"] = int((time.time() - start_time) * 1000)
            return result, telemetry
        
        # Calculate cluster statistics
        total_clustered_docs = sum(c['member_count'] for c in clusters)
        avg_confidence = sum(c['confidence_score'] for c in clusters) / len(clusters)
        
        # Check for weak signals
        weak_signals = avg_confidence < WEAK_SIGNAL_THRESHOLD
        
        if weak_signals:
            logger.warning(f"Weak signals detected - avg confidence {avg_confidence:.3f} < {WEAK_SIGNAL_THRESHOLD}")
            telemetry["weak_signals_detected"] = True
            telemetry["fallback_reason"] = "weak_signals"
            telemetry["latency_ms"] = int((time.time() - start_time) * 1000)
            return result, telemetry
        
        # Extract shared themes from clusters
        shared_themes = []
        for cluster in clusters:
            shared_themes.append({
                "theme": cluster['theme_label'],
                "document_count": cluster['member_count'],
                "confidence": cluster['confidence_score']
            })
        
        # Build successful result
        result = {
            "semantic_clusters": clusters,
            "cluster_confidence": round(avg_confidence, 3),
            "cross_file_overlap_detected": len(clusters) > 0,
            "shared_themes": shared_themes,
            "processing_mode": mode
        }
        
        # Build telemetry
        telemetry = {
            "cross_file_analysis_used": True,
            "cluster_count": len(clusters),
            "avg_cluster_confidence": round(avg_confidence, 3),
            "documents_clustered": total_clustered_docs,
            "documents_unclustered": len(per_document_summaries) - total_clustered_docs,
            "weak_signals_detected": False,
            "fallback_reason": None,
            "latency_ms": int((time.time() - start_time) * 1000)
        }
        
        logger.info(
            f"Cross-file analysis complete - "
            f"clusters={len(clusters)}, "
            f"avg_confidence={avg_confidence:.3f}, "
            f"docs_clustered={total_clustered_docs}/{len(per_document_summaries)}, "
            f"latency={telemetry['latency_ms']}ms"
        )
        
        return result, telemetry
        
    except Exception as e:
        logger.error(f"Error in cross-file semantic analysis: {type(e).__name__} - {str(e)}")
        telemetry["fallback_reason"] = f"error_{type(e).__name__}"
        telemetry["latency_ms"] = int((time.time() - start_time) * 1000)
        return result, telemetry


def detect_overlapping_concepts(
    semantic_clusters: List[Dict[str, Any]],
    per_document_summaries: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Detect specific overlapping concepts across clustered documents.
    
    Args:
        semantic_clusters: List of document clusters
        per_document_summaries: Original document summaries
        
    Returns:
        List of overlapping concept dicts
    """
    overlaps = []
    
    for cluster in semantic_clusters:
        theme = cluster.get('theme_label', '')
        member_docs = cluster.get('member_documents', [])
        
        if len(member_docs) >= 2:
            overlaps.append({
                "concept": theme,
                "appears_in": member_docs,
                "frequency": len(member_docs),
                "confidence": cluster.get('confidence_score', 0.0)
            })
    
    # Sort by frequency and confidence
    overlaps.sort(key=lambda x: (x['frequency'], x['confidence']), reverse=True)
    
    return overlaps
