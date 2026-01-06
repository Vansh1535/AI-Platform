"""
Document summarization service with RAG-first extractive + hybrid LLM fallback.

Modes:
- extractive: Pure RAG, no LLM (safest, no hallucination)
- hybrid: RAG + LLM when confidence low (intelligent fallback)
- auto: Automatically choose based on confidence

Maintains transparency metadata consistent with RAG answer pipeline.
"""

import time
import re
from typing import Dict, Any, List, Tuple, Optional
from collections import Counter
from app.core.logging import setup_logger
from app.rag.retrieval.search import search
from app.llm.router import call_llm, is_llm_enabled
from app.core.config import settings
from app.utils.graceful_response import graceful_fallback, success_message

logger = setup_logger()

# Confidence threshold for hybrid mode fallback
CONFIDENCE_THRESHOLD = 0.55
MIN_CHUNKS_EXTRACTIVE = 2


def score_sentence(
    sentence: str, 
    position_in_chunk: int, 
    chunk_index: int,
    is_heading: bool = False
) -> float:
    """
    Score a sentence for extractive summarization quality.
    
    Scoring factors:
    - Length: Prefer 40-150 chars (too short = fragment, too long = complex)
    - Position: Earlier sentences preferred
    - Heading: Bonus for section titles/headings
    - Content quality: Penalize questions, prefer statements
    
    Args:
        sentence: The sentence text
        position_in_chunk: Position within chunk (0-based)
        chunk_index: Which chunk this came from
        is_heading: Whether this is a heading/title
        
    Returns:
        Score (higher = better for summary)
    """
    if not sentence or len(sentence.strip()) < 10:
        return 0.0
    
    score = 0.0
    length = len(sentence)
    
    # Length scoring (bell curve around 80 chars)
    if 40 <= length <= 150:
        # Optimal range
        length_score = 1.0 - abs(length - 80) / 110  # Peak at 80 chars
        score += length_score * 3.0
    elif length < 40:
        # Too short (likely fragment)
        score += (length / 40) * 1.5
    else:
        # Too long (penalize complexity)
        score += max(0, 2.0 - (length - 150) / 100)
    
    # Position bonus (earlier = better)
    if position_in_chunk == 0:
        score += 2.0  # First sentence in chunk
    elif position_in_chunk == 1:
        score += 1.0  # Second sentence
    else:
        score += max(0, 0.5 - position_in_chunk * 0.1)
    
    # Chunk position (earlier chunks slightly preferred)
    score += max(0, 1.0 - chunk_index * 0.1)
    
    # Heading bonus
    if is_heading:
        score += 3.0
    
    # Content quality heuristics
    sentence_lower = sentence.lower().strip()
    
    # Penalize questions (usually not good for summaries)
    if sentence.endswith('?'):
        score -= 1.0
    
    # Bonus for key informational phrases
    info_markers = ['is a', 'are ', 'includes', 'contains', 'involves', 'refers to', 'means']
    if any(marker in sentence_lower for marker in info_markers):
        score += 0.5
    
    # Penalize pronouns without clear context
    if sentence_lower.startswith(('he ', 'she ', 'it ', 'they ', 'this ', 'that ')):
        score -= 0.5
    
    # Bonus for sentences with numbers/data
    if re.search(r'\d+', sentence):
        score += 0.3
    
    return max(0.0, score)


def compute_sentence_similarity(sent1: str, sent2: str) -> float:
    """
    Compute simple word-overlap similarity between two sentences.
    Used to detect near-duplicates.
    
    Args:
        sent1: First sentence
        sent2: Second sentence
        
    Returns:
        Similarity score 0-1 (1 = identical)
    """
    words1 = set(sent1.lower().split())
    words2 = set(sent2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1 & words2
    union = words1 | words2
    
    return len(intersection) / len(union) if union else 0.0


def extract_key_sentences(
    chunks: List[Dict[str, Any]], 
    max_sentences: int = 5,
    summary_length: str = "medium"
) -> List[Tuple[str, float]]:
    """
    Extract key sentences from retrieved chunks using advanced scoring.
    
    Args:
        chunks: List of retrieved chunks with text and metadata
        max_sentences: Maximum sentences to extract
        summary_length: "short" (3), "medium" (5), "detailed" (8)
        
    Returns:
        List of (sentence, score) tuples, sorted by score descending
    """
    # Adjust max_sentences based on length preference
    length_map = {"short": 3, "medium": 5, "detailed": 8}
    max_sentences = length_map.get(summary_length, max_sentences)
    
    scored_sentences = []
    
    for chunk_idx, chunk in enumerate(chunks):
        text = chunk.get("chunk", "")
        
        # Check if this looks like a heading
        is_likely_heading = (
            len(text) < 100 and 
            not text.endswith('.') and 
            (text.startswith('#') or text.isupper() or text.istitle())
        )
        
        # Split by periods, filter empty/short
        sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 10]
        
        for sent_idx, sentence in enumerate(sentences):
            # Score this sentence
            score = score_sentence(
                sentence=sentence,
                position_in_chunk=sent_idx,
                chunk_index=chunk_idx,
                is_heading=is_likely_heading and sent_idx == 0
            )
            
            scored_sentences.append((sentence, score))
    
    # Sort by score descending
    scored_sentences.sort(key=lambda x: x[1], reverse=True)
    
    # Remove near-duplicates
    unique_sentences = []
    for sentence, score in scored_sentences:
        is_duplicate = False
        for existing_sent, _ in unique_sentences:
            similarity = compute_sentence_similarity(sentence, existing_sent)
            if similarity > 0.7:  # 70% overlap = duplicate
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_sentences.append((sentence, score))
        
        # Stop when we have enough
        if len(unique_sentences) >= max_sentences:
            break
    
    return unique_sentences


def build_extractive_summary(
    chunks: List[Dict[str, Any]], 
    document_id: str,
    summary_length: str = "medium"
) -> Tuple[str, Dict[str, Any]]:
    """
    Build extractive summary from retrieved chunks without LLM.
    
    Args:
        chunks: Retrieved chunks
        document_id: Document identifier
        summary_length: "short", "medium", or "detailed"
        
    Returns:
        Tuple of (summary_text, telemetry)
    """
    if not chunks:
        return (
            "No relevant content found in document.",
            {
                "mode_used": "extractive",
                "chunks_used": 0,
                "summary_type": "no_content",
                "summary_length": summary_length
            }
        )
    
    # Extract key sentences with scoring
    scored_sentences = extract_key_sentences(chunks, summary_length=summary_length)
    
    # Build structured summary
    summary_parts = [
        f"Document Summary (ID: {document_id})",
        "",
        "Key Points:",
    ]
    
    for i, (sentence, score) in enumerate(scored_sentences, 1):
        summary_parts.append(f"{i}. {sentence}")
    
    summary_parts.append("")
    summary_parts.append(f"(Based on {len(chunks)} retrieved chunks)")
    
    summary = "\n".join(summary_parts)
    
    telemetry = {
        "mode_used": "extractive",
        "chunks_used": len(chunks),
        "key_sentences": len(scored_sentences),
        "summary_type": "extractive_outline",
        "summary_length": summary_length,
        "llm_used": False
    }
    
    return summary, telemetry


def build_hybrid_summary(
    chunks: List[Dict[str, Any]],
    document_id: str,
    query: str = "document summary"
) -> Tuple[str, Dict[str, Any]]:
    """
    Build hybrid summary using RAG chunks + LLM synthesis.
    Used when confidence is low or few chunks available.
    
    Args:
        chunks: Retrieved chunks
        document_id: Document identifier
        query: Query context for LLM
        
    Returns:
        Tuple of (summary_text, telemetry)
    """
    start_time = time.time()
    
    if not chunks:
        return (
            "No relevant content found in document for summarization.",
            {
                "mode_used": "hybrid",
                "chunks_used": 0,
                "summary_type": "no_content",
                "llm_used": False,
                "latency_ms_llm": 0
            }
        )
    
    # Check LLM availability
    if not is_llm_enabled():
        logger.warning("LLM not available, falling back to extractive mode")
        return build_extractive_summary(chunks, document_id)
    
    # Build context from chunks
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        text = chunk.get("chunk", "")
        context_parts.append(f"[Chunk {i}]\n{text}")
    
    context = "\n\n".join(context_parts)
    
    # Build LLM prompt for summarization
    prompt = f"""Summarize the following document content. Create a concise, structured summary highlighting the main points.

IMPORTANT: Only use information from the provided chunks. Do not add external information.

Document ID: {document_id}
Retrieved Content:
{context}

Provide a clear, bullet-pointed summary of the key information."""
    
    try:
        # Call LLM
        llm_start = time.time()
        llm_response = call_llm(
            prompt=prompt,
            system="You are a document summarizer. Create concise, accurate summaries based only on provided content.",
            temperature=0.3  # Lower temperature for factual summarization
        )
        llm_latency = int((time.time() - llm_start) * 1000)
        
        summary_text = llm_response["text"]
        provider = llm_response["provider"]
        
        telemetry = {
            "mode_used": "hybrid",
            "chunks_used": len(chunks),
            "summary_type": "llm_synthesized",
            "llm_used": True,
            "provider": provider,
            "latency_ms_llm": llm_latency
        }
        
        logger.info(f"Hybrid summary generated using {provider} in {llm_latency}ms")
        
        return summary_text, telemetry
        
    except Exception as e:
        logger.error(f"LLM summarization failed: {str(e)}, falling back to extractive")
        # Fallback to extractive on LLM error
        return build_extractive_summary(chunks, document_id)


def summarize_document(
    document_id: str,
    mode: str = "auto",
    max_chunks: int = 5,
    summary_length: str = "medium"
) -> Tuple[str, Dict[str, Any]]:
    """
    Generate document summary using RAG-first approach with hybrid fallback.
    
    Modes:
    - auto: Automatically choose extractive or hybrid based on confidence
    - extractive: Pure RAG, no LLM (safest, no hallucination)
    - hybrid: RAG + LLM synthesis (when confidence low or explicit request)
    
    Args:
        document_id: Document identifier to summarize
        mode: Summarization mode (auto, extractive, hybrid)
        max_chunks: Maximum chunks to retrieve (default: 5)
        summary_length: Summary length - "short" (3 points), "medium" (5), "detailed" (8)
        
    Returns:
        Tuple of (summary_text, telemetry_dict)
        
    Raises:
        ValueError: If mode is invalid
    """
    start_time = time.time()
    
    # Validate mode
    valid_modes = ["auto", "extractive", "hybrid"]
    if mode not in valid_modes:
        raise ValueError(f"Invalid mode '{mode}'. Must be one of: {', '.join(valid_modes)}")
    
    # Validate summary_length
    valid_lengths = ["short", "medium", "detailed"]
    if summary_length not in valid_lengths:
        logger.warning(f"Invalid summary_length '{summary_length}', defaulting to 'medium'")
        summary_length = "medium"
    
    logger.info(f"Starting document summarization - ID: {document_id}, Mode: {mode}, Length: {summary_length}, Max Chunks: {max_chunks}")
    
    # Initialize telemetry
    telemetry = {
        "routing": "summarizer_tool",
        "mode_requested": mode,
        "mode_used": None,
        "document_id": document_id,
        "confidence_top": None,
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "retrieval_pass": None,
        "top_k_scores": [],
        "chunks_used": 0,
        "latency_ms_retrieval": 0,
        "latency_ms_llm": 0,
        "latency_ms_total": 0,
        "provider": None,
        "error_class": None
    }
    
    try:
        # Step 1: Retrieve relevant chunks using RAG with document_id filtering
        logger.info("Step 1: Retrieving chunks for summarization...")
        retrieval_start = time.time()
        
        # Use document_id for filtered retrieval (deterministic results)
        query = f"{document_id} complete content full text"
        results, retrieval_telemetry = search(
            query, 
            top_k=max_chunks,
            document_id=document_id  # Filter by document_id at retrieval level
        )
        
        retrieval_latency = int((time.time() - retrieval_start) * 1000)
        telemetry["latency_ms_retrieval"] = retrieval_latency
        
        # Merge retrieval telemetry
        telemetry.update({
            "confidence_top": retrieval_telemetry.get("confidence_top"),
            "retrieval_pass": retrieval_telemetry.get("retrieval_pass"),
            "top_k_scores": retrieval_telemetry.get("top_k_scores", []),
            "document_id_filter": retrieval_telemetry.get("document_id_filter")  # Add document_id filter info
        })
        
        num_chunks = len(results)
        logger.info(f"Retrieved {num_chunks} chunks (top score: {telemetry['confidence_top']:.3f})")
        
        # Check for insufficient content early
        if num_chunks == 0:
            graceful_data = graceful_fallback(
                "summarize_no_content",
                reason="no_chunks_retrieved",
                meta=telemetry
            )
            telemetry.update(graceful_data)
            telemetry["mode_used"] = "extractive"  # Default mode when no content
            telemetry["chunks_used"] = 0
            telemetry["latency_ms_total"] = int((time.time() - start_time) * 1000)
            return "No content available to summarize for this document.", telemetry
        
        if num_chunks < MIN_CHUNKS_EXTRACTIVE:
            logger.warning(f"Document has very limited content ({num_chunks} chunks)")
        
        # Step 2: Determine summarization mode
        if mode == "auto":
            # Auto-select based on confidence and chunk count
            top_confidence = telemetry.get("confidence_top", 0)
            
            if num_chunks < MIN_CHUNKS_EXTRACTIVE:
                selected_mode = "hybrid"
                logger.info(f"Auto-selecting HYBRID mode: too few chunks ({num_chunks} < {MIN_CHUNKS_EXTRACTIVE})")
            elif top_confidence < CONFIDENCE_THRESHOLD:
                selected_mode = "hybrid"
                logger.info(f"Auto-selecting HYBRID mode: low confidence ({top_confidence:.3f} < {CONFIDENCE_THRESHOLD})")
            else:
                selected_mode = "extractive"
                logger.info(f"Auto-selecting EXTRACTIVE mode: sufficient chunks + high confidence")
        else:
            selected_mode = mode
            logger.info(f"Using explicit mode: {selected_mode}")
        
        # Step 3: Generate summary based on selected mode
        if selected_mode == "extractive":
            summary, mode_telemetry = build_extractive_summary(results, document_id, summary_length)
        else:  # hybrid
            summary, mode_telemetry = build_hybrid_summary(results, document_id, query)
        
        # Merge mode-specific telemetry
        telemetry.update(mode_telemetry)
        
        # Step 4: Add graceful messaging based on conditions
        # Check for low quality / degraded cases
        top_confidence = telemetry.get("confidence_top", 0)
        
        if num_chunks < 3:
            # Very limited content
            graceful_data = graceful_fallback(
                "summarize_too_short",
                reason=f"only_{num_chunks}_chunks",
                meta={"confidence": top_confidence}
            )
            telemetry.update(graceful_data)
        elif telemetry.get("mode_used") == "extractive" and selected_mode == "hybrid":
            # Fell back to extractive when hybrid was requested
            graceful_data = graceful_fallback(
                "summarize_extractive_fallback",
                reason="llm_unavailable_or_failed",
                meta={"mode_requested": mode}
            )
            telemetry.update(graceful_data)
        elif top_confidence < CONFIDENCE_THRESHOLD * 0.8:
            # Low quality chunks
            graceful_data = graceful_fallback(
                "summarize_low_quality",
                reason=f"confidence={top_confidence:.3f}",
                meta={"confidence": top_confidence}
            )
            telemetry.update(graceful_data)
        else:
            # Success
            graceful_data = success_message("summarize_document", {"chunks": num_chunks})
            telemetry.update(graceful_data)
        
        # Step 5: Calculate total latency
        total_latency = int((time.time() - start_time) * 1000)
        telemetry["latency_ms_total"] = total_latency
        
        logger.info(
            f"Summarization complete - Mode: {telemetry['mode_used']}, "
            f"Chunks: {num_chunks}, Total: {total_latency}ms"
        )
        
        # Ensure complete telemetry before returning
        from app.core.telemetry import ensure_complete_telemetry
        telemetry = ensure_complete_telemetry(telemetry)
        
        return summary, telemetry
        
    except Exception as e:
        error_msg = f"Summarization failed: {str(e)}"
        logger.error(error_msg)
        
        total_latency = int((time.time() - start_time) * 1000)
        telemetry["latency_ms_total"] = total_latency
        telemetry["error_class"] = type(e).__name__
        
        # Ensure complete telemetry before returning error
        from app.core.telemetry import ensure_complete_telemetry
        telemetry = ensure_complete_telemetry(telemetry)
        telemetry["fallback_triggered"] = True
        telemetry["degradation_level"] = "failed"
        
        # Return graceful error
        return (
            f"Unable to generate summary for document {document_id}. {str(e)}",
            telemetry
        )


def summarize_document_by_source(
    source: str,
    mode: str = "auto",
    max_chunks: int = 5
) -> Tuple[str, Dict[str, Any]]:
    """
    Generate summary by searching for document source instead of document_id.
    Useful when document_id is not known but source name is.
    
    Args:
        source: Document source identifier
        mode: Summarization mode
        max_chunks: Maximum chunks to retrieve
        
    Returns:
        Tuple of (summary_text, telemetry_dict)
    """
    logger.info(f"Summarizing by source: {source}")
    
    # Use source as the search query to find relevant document
    return summarize_document(
        document_id=f"source:{source}",
        mode=mode,
        max_chunks=max_chunks
    )
