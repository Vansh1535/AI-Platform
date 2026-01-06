"""
Semantic Theme Clustering for Multi-Document Insights

Provides semantic similarity-based clustering of themes and concepts extracted
from multiple documents. Uses sentence embeddings to group similar phrases by
meaning rather than exact wording.

Key Features:
- Embedding-based similarity clustering
- Confidence scoring for clusters
- Cross-document theme grouping
- Source evidence linking
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)

# Clustering thresholds
SIMILARITY_THRESHOLD = 0.35  # Minimum similarity to form cluster
MIN_CLUSTER_SIZE = 2  # Minimum members to be a valid cluster
EVIDENCE_PREVIEW_LENGTH = 200  # Character limit for evidence previews


def get_embedding_function():
    """
    Get the embedding function (reuse from Phase A).
    Falls back gracefully if embeddings unavailable.
    
    Returns:
        Embedding function or None if unavailable
    """
    try:
        from app.rag.retrieval.search import get_embedding_model
        model = get_embedding_model()
        
        # Create wrapper function that returns list of embeddings
        def embed_texts(texts: List[str]) -> List[List[float]]:
            embeddings = model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        
        # Test that it works
        test_result = embed_texts(["test"])
        if test_result and len(test_result) > 0:
            return embed_texts
        else:
            logger.warning("Embedding function returned invalid result")
            return None
            
    except Exception as e:
        logger.warning(f"Could not load embedding function: {str(e)}")
        return None


def compute_cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Cosine similarity score (0-1)
    """
    try:
        # Normalize vectors
        vec1_norm = vec1 / (np.linalg.norm(vec1) + 1e-10)
        vec2_norm = vec2 / (np.linalg.norm(vec2) + 1e-10)
        
        # Compute dot product
        similarity = np.dot(vec1_norm, vec2_norm)
        
        # Ensure in valid range
        return max(0.0, min(1.0, float(similarity)))
        
    except Exception as e:
        logger.error(f"Error computing cosine similarity: {str(e)}")
        return 0.0


def cluster_themes_by_similarity(
    phrases: List[Dict[str, Any]],
    embedding_function,
    similarity_threshold: float = SIMILARITY_THRESHOLD
) -> List[Dict[str, Any]]:
    """
    Cluster phrases by semantic similarity using embeddings.
    
    Args:
        phrases: List of phrase dicts with 'phrase', 'frequency', 'document_ids'
        embedding_function: Function to generate embeddings
        similarity_threshold: Minimum similarity to group phrases
        
    Returns:
        List of cluster dicts with theme_label, members, documents_involved, confidence
    """
    if not phrases or not embedding_function:
        logger.warning("No phrases or embedding function provided for clustering")
        return []
    
    try:
        # Extract phrase texts
        phrase_texts = [p.get('phrase', p.get('theme', '')) for p in phrases]
        
        if not phrase_texts:
            logger.warning("No valid phrase texts found")
            return []
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(phrase_texts)} phrases...")
        embeddings = embedding_function(phrase_texts)
        
        if not embeddings or len(embeddings) != len(phrase_texts):
            logger.error("Embedding generation failed or returned wrong size")
            return []
        
        # Convert to numpy arrays
        embeddings = [np.array(emb) for emb in embeddings]
        
        # Initialize clusters (each phrase starts as its own cluster)
        clusters = []
        used_indices = set()
        
        # Greedy clustering: for each phrase, find all similar phrases
        for i, phrase in enumerate(phrase_texts):
            if i in used_indices:
                continue
            
            # Start new cluster with this phrase
            cluster_members = [phrase]
            cluster_indices = [i]
            cluster_docs = set(phrases[i].get('document_ids', []))
            similarities = []
            
            # Find similar phrases
            for j in range(i + 1, len(phrase_texts)):
                if j in used_indices:
                    continue
                
                similarity = compute_cosine_similarity(embeddings[i], embeddings[j])
                
                if similarity >= similarity_threshold:
                    cluster_members.append(phrase_texts[j])
                    cluster_indices.append(j)
                    cluster_docs.update(phrases[j].get('document_ids', []))
                    similarities.append(similarity)
                    used_indices.add(j)
            
            # Mark primary phrase as used
            used_indices.add(i)
            
            # Calculate cluster confidence
            if similarities:
                avg_similarity = sum(similarities) / len(similarities)
            else:
                avg_similarity = 1.0  # Single-member cluster has perfect "similarity"
            
            # Only include clusters with multiple members or high-value single members
            if len(cluster_members) >= MIN_CLUSTER_SIZE or (
                len(cluster_members) == 1 and phrases[i].get('frequency', 0) >= 2
            ):
                clusters.append({
                    "theme_label": phrase,  # Use first phrase as representative
                    "members": cluster_members,
                    "documents_involved": sorted(list(cluster_docs)),
                    "confidence": avg_similarity,
                    "member_count": len(cluster_members)
                })
        
        # Sort by confidence and member count
        clusters.sort(key=lambda x: (x['confidence'], x['member_count']), reverse=True)
        
        logger.info(f"Created {len(clusters)} semantic clusters from {len(phrases)} phrases")
        
        return clusters
        
    except Exception as e:
        logger.error(f"Error during semantic clustering: {str(e)}")
        return []


def extract_evidence_links(
    summaries: List[Dict[str, Any]],
    theme: str,
    embedding_function,
    max_evidence: int = 3
) -> List[Dict[str, Any]]:
    """
    Extract source-linked evidence for a given theme from document summaries.
    
    Enhanced to provide:
    - Document source references
    - Evidence text excerpts
    - Similarity confidence scores
    - Document metadata (chunks used, mode)
    
    Args:
        summaries: List of document summary dicts
        theme: Theme phrase to find evidence for
        embedding_function: Function to generate embeddings
        max_evidence: Maximum evidence items to return
        
    Returns:
        List of evidence dicts with document_id, text_preview, similarity, document_metadata
    """
    if not summaries or not theme or not embedding_function:
        return []
    
    try:
        # Generate embedding for theme
        theme_embedding = embedding_function([theme])[0]
        theme_embedding = np.array(theme_embedding)
        
        evidence_items = []
        
        # For each document summary, compute similarity
        for summary_dict in summaries:
            doc_id = summary_dict.get('document_id', '')
            summary_text = summary_dict.get('summary', '')
            
            if not summary_text:
                continue
            
            # Split summary into sentences for fine-grained evidence
            sentences = [s.strip() for s in summary_text.split('.') if len(s.strip()) > 20]
            
            if not sentences:
                # Fallback to full summary
                sentences = [summary_text[:EVIDENCE_PREVIEW_LENGTH]]
            
            # Generate embeddings for sentences
            sentence_embeddings = embedding_function(sentences)
            
            # Find most similar sentence
            best_similarity = 0.0
            best_sentence = sentences[0]
            
            for sent, sent_emb in zip(sentences, sentence_embeddings):
                similarity = compute_cosine_similarity(theme_embedding, np.array(sent_emb))
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_sentence = sent
            
            # Only include if similarity is above threshold
            if best_similarity >= SIMILARITY_THRESHOLD:
                # Create preview
                preview = best_sentence[:EVIDENCE_PREVIEW_LENGTH]
                if len(best_sentence) > EVIDENCE_PREVIEW_LENGTH:
                    preview += "..."
                
                # Build evidence with enhanced metadata
                evidence_items.append({
                    "document_id": doc_id,
                    "text_preview": preview,
                    "similarity": round(best_similarity, 3),
                    "confidence_level": "high" if best_similarity >= 0.7 else "medium" if best_similarity >= 0.5 else "acceptable",
                    "chunks_used": summary_dict.get('chunks_used', 0),
                    "summary_mode": summary_dict.get('mode_used', 'unknown')
                })
        
        # Sort by similarity and limit
        evidence_items.sort(key=lambda x: x['similarity'], reverse=True)
        return evidence_items[:max_evidence]
        
    except Exception as e:
        logger.error(f"Error extracting evidence links: {str(e)}")
        return []


def _fallback_no_clustering(reason: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Return fallback structure when semantic clustering cannot be performed.
    
    Args:
        reason: Reason for fallback
        
    Returns:
        Tuple of (empty clusters list, metadata dict)
    """
    metadata = {
        "semantic_clustering_used": False,
        "cluster_count": 0,
        "avg_cluster_confidence": None,
        "evidence_links_available": False,
        "fallback_reason": reason
    }
    logger.info(f"semantic_clustering=fallback reason={reason}")
    return [], metadata


def create_semantic_clusters(
    themes: List[Dict[str, Any]],
    overlaps: List[Dict[str, Any]],
    summaries: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Create semantic clusters from extracted themes and overlaps.
    Main entry point for semantic clustering enhancement.
    
    Args:
        themes: List of extracted theme/phrase dicts
        overlaps: List of overlapping theme dicts
        summaries: List of per-document summaries for evidence linking
        
    Returns:
        Tuple of (clusters, metadata)
    """
    try:
        # Get embedding function
        embedding_function = get_embedding_function()
        
        if not embedding_function:
            logger.warning("Semantic clustering disabled — no embedding function available")
            return _fallback_no_clustering("embedding_unavailable")
        
        # Prepare phrases for clustering (combine themes and overlaps)
        phrases_for_clustering = []
        
        # Add themes (handle both list of strings and list of dicts)
        for theme in themes:
            if isinstance(theme, str):
                # Theme is a simple string
                phrase_text = theme
                phrases_for_clustering.append({
                    "phrase": phrase_text,
                    "frequency": 1,
                    "document_ids": []
                })
            elif isinstance(theme, dict):
                # Theme is a dict with metadata
                phrase_text = theme.get('phrase', theme.get('theme', ''))
                if phrase_text:
                    phrases_for_clustering.append({
                        "phrase": phrase_text,
                        "frequency": theme.get('frequency', 1),
                        "document_ids": theme.get('document_ids', [])
                    })
        
        # Add overlaps
        for overlap in overlaps:
            if isinstance(overlap, dict):
                phrase_text = overlap.get('theme', '')
                if phrase_text:
                    phrases_for_clustering.append({
                        "phrase": phrase_text,
                        "frequency": overlap.get('frequency', 1),
                        "document_ids": overlap.get('document_ids', [])
                    })
        
        if not phrases_for_clustering:
            logger.warning("No phrases available for clustering")
            return _fallback_no_clustering("no_phrases_to_cluster")
        
        # Check minimum sample size
        if len(phrases_for_clustering) < MIN_CLUSTER_SIZE:
            logger.warning(f"Insufficient phrases for clustering: {len(phrases_for_clustering)} < {MIN_CLUSTER_SIZE}")
            return _fallback_no_clustering("insufficient_samples")
        
        # Perform clustering
        logger.info(f"Starting semantic clustering of {len(phrases_for_clustering)} phrases...")
        clusters = cluster_themes_by_similarity(
            phrases_for_clustering,
            embedding_function,
            similarity_threshold=SIMILARITY_THRESHOLD
        )
        
        if not clusters:
            logger.warning("Semantic clustering produced no results")
            return _fallback_no_clustering("clustering_produced_no_results")
        
        # Add evidence links to each cluster
        logger.info(f"Adding evidence links to {len(clusters)} clusters...")
        for cluster in clusters:
            theme_label = cluster.get('theme_label', '')
            evidence = extract_evidence_links(
                summaries,
                theme_label,
                embedding_function,
                max_evidence=3
            )
            cluster['evidence'] = evidence
            cluster['evidence_count'] = len(evidence)
            
            if evidence:
                cluster['evidence_score_avg'] = round(
                    sum(e['similarity'] for e in evidence) / len(evidence),
                    3
                )
                # Add document references list for quick lookup
                cluster['evidence_documents'] = sorted(list(set(e['document_id'] for e in evidence)))
                # Count high-confidence evidence
                cluster['high_confidence_evidence_count'] = sum(1 for e in evidence if e.get('confidence_level') == 'high')
            else:
                cluster['evidence_score_avg'] = 0.0
                cluster['evidence_documents'] = []
                cluster['high_confidence_evidence_count'] = 0
        
        # Validate cluster quality before marking as successful
        avg_confidence = sum(c['confidence'] for c in clusters) / len(clusters)
        
        if avg_confidence < SIMILARITY_THRESHOLD:
            logger.warning(f"Cluster confidence too low: {avg_confidence:.3f} < {SIMILARITY_THRESHOLD}")
            return _fallback_no_clustering("low_confidence_clusters")
        
        # Only mark as successful if embeddings worked AND valid clusters formed AND confidence meets threshold
        metadata = {
            "semantic_clustering_used": True,
            "cluster_count": len(clusters),
            "avg_cluster_confidence": round(avg_confidence, 3),
            "evidence_links_available": any(c.get('evidence_count', 0) > 0 for c in clusters),
            "fallback_reason": None
        }
        
        logger.info(f"semantic_clustering=success clusters={len(clusters)} avg_confidence={avg_confidence:.3f}")
        
        logger.info(
            f"Semantic clustering complete - {len(clusters)} clusters, "
            f"avg confidence: {metadata['avg_cluster_confidence']}"
        )
        
        return clusters, metadata
        
    except Exception as e:
        logger.error(f"Error in semantic clustering: {str(e)}")
        return _fallback_no_clustering(f"error_{type(e).__name__}")
