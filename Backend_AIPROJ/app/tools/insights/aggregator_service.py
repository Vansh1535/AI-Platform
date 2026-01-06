"""
Multi-File Insights Aggregator Service (Phase C)

Processes multiple documents to generate:
- Per-document summaries (using Phase B summarizer)
- Cross-document aggregated insights (themes, overlaps, differences)
- RAG-first approach with optional LLM synthesis
"""

import time
import re
from typing import List, Dict, Any, Tuple
from collections import Counter
from app.core.logging import setup_logger
from app.tools.summarizer import summarize_document
from app.llm.router import is_llm_enabled, call_llm
from app.utils.graceful_response import graceful_fallback, success_message

logger = setup_logger("INFO")

# Minimum documents required for aggregation
MIN_DOCUMENTS_FOR_AGGREGATION = 2


def extract_key_phrases(summary_text: str, top_n: int = 10) -> List[str]:
    """
    Extract key phrases from summary text using simple heuristics.
    RAG-first approach - no LLM needed.
    
    Args:
        summary_text: The summary text to analyze
        top_n: Number of top phrases to return
        
    Returns:
        List of key phrases
    """
    # Remove document summary headers and numbering
    text = re.sub(r'Document Summary.*?\n', '', summary_text, flags=re.IGNORECASE)
    text = re.sub(r'Key Points:?\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^\d+\.\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\(Based on.*?\)', '', text, flags=re.IGNORECASE)
    
    # Split into sentences
    sentences = re.split(r'[.!?]\s+', text)
    
    # Extract capitalized phrases (likely important terms)
    key_phrases = []
    for sentence in sentences:
        # Find capitalized multi-word phrases
        phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', sentence)
        key_phrases.extend(phrases)
        
        # Find important single words (capitalized, longer than 4 chars)
        words = re.findall(r'\b[A-Z][a-z]{4,}\b', sentence)
        key_phrases.extend(words)
    
    # Count frequency
    phrase_counts = Counter(key_phrases)
    
    # Return top N most common
    return [phrase for phrase, _ in phrase_counts.most_common(top_n)]


def find_overlapping_themes(summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Find themes that appear across multiple documents.
    RAG-first: Extract from retrieved summaries, no hallucination.
    
    Args:
        summaries: List of document summaries with metadata
        
    Returns:
        List of overlapping themes with document references
    """
    # Extract phrases from each document
    doc_phrases = {}
    for summary in summaries:
        doc_id = summary['document_id']
        phrases = extract_key_phrases(summary['summary'], top_n=15)
        doc_phrases[doc_id] = set(phrases)
    
    # Find phrases appearing in multiple documents
    all_phrases = [phrase for phrases in doc_phrases.values() for phrase in phrases]
    phrase_counts = Counter(all_phrases)
    
    # Overlapping themes (appear in 2+ docs)
    overlaps = []
    for phrase, count in phrase_counts.items():
        if count >= 2:
            # Find which documents contain this phrase
            docs_with_phrase = [
                doc_id for doc_id, phrases in doc_phrases.items() 
                if phrase in phrases
            ]
            overlaps.append({
                "theme": phrase,
                "frequency": count,
                "document_ids": docs_with_phrase
            })
    
    # Sort by frequency
    overlaps.sort(key=lambda x: x['frequency'], reverse=True)
    
    return overlaps[:10]  # Top 10 overlapping themes


def extract_unique_aspects(summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract aspects unique to each document.
    RAG-first: Based only on retrieved content.
    
    Args:
        summaries: List of document summaries with metadata
        
    Returns:
        List of unique aspects per document
    """
    # Extract phrases from each document
    doc_phrases = {}
    for summary in summaries:
        doc_id = summary['document_id']
        phrases = extract_key_phrases(summary['summary'], top_n=15)
        doc_phrases[doc_id] = set(phrases)
    
    # Find unique phrases (appear in only one doc)
    unique_aspects = []
    for doc_id, phrases in doc_phrases.items():
        # Find phrases not in any other document
        other_phrases = set()
        for other_doc_id, other_doc_phrases in doc_phrases.items():
            if other_doc_id != doc_id:
                other_phrases.update(other_doc_phrases)
        
        unique = phrases - other_phrases
        if unique:
            unique_aspects.append({
                "document_id": doc_id,
                "unique_themes": list(unique)[:5]  # Top 5 unique themes
            })
    
    return unique_aspects


def extract_entities(summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract entities (names, organizations, technical terms) from summaries.
    Simple pattern-based extraction - no NLP library needed.
    
    Args:
        summaries: List of document summaries with metadata
        
    Returns:
        List of entities with frequency and document references
    """
    entity_docs = {}
    
    for summary in summaries:
        doc_id = summary['document_id']
        text = summary['summary']
        
        # Extract capitalized multi-word entities
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text)
        
        for entity in entities:
            if entity not in entity_docs:
                entity_docs[entity] = []
            if doc_id not in entity_docs[entity]:
                entity_docs[entity].append(doc_id)
    
    # Format as list with frequencies
    result = []
    for entity, docs in entity_docs.items():
        result.append({
            "entity": entity,
            "frequency": len(docs),
            "document_ids": docs
        })
    
    # Sort by frequency
    result.sort(key=lambda x: x['frequency'], reverse=True)
    
    return result[:20]  # Top 20 entities


def detect_risk_signals(summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detect potential risk signals or negative indicators in summaries.
    Pattern-based detection of concerning language.
    
    Args:
        summaries: List of document summaries with metadata
        
    Returns:
        List of risk signals found
    """
    risk_patterns = [
        r'\b(fail(?:ure|ed)?|error|problem|issue|bug|crash)\b',
        r'\b(risk|threat|vulnerability|concern|warning)\b',
        r'\b(deprecat(?:ed|ion)?|obsolete|legacy|unsupported)\b',
        r'\b(critical|urgent|immediate|emergency)\b',
        r'\b(loss|damage|corrupt(?:ed|ion)?|breach)\b'
    ]
    
    risk_signals = []
    
    for summary in summaries:
        doc_id = summary['document_id']
        text = summary['summary'].lower()
        
        found_risks = []
        for pattern in risk_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            found_risks.extend(matches)
        
        if found_risks:
            # Get context sentences for risks
            sentences = re.split(r'[.!?]\s+', summary['summary'])
            risk_contexts = []
            
            for risk_term in set(found_risks):
                for sentence in sentences:
                    if risk_term.lower() in sentence.lower():
                        risk_contexts.append({
                            "term": risk_term,
                            "context": sentence.strip()[:150]  # First 150 chars
                        })
                        break  # One context per term
            
            if risk_contexts:
                risk_signals.append({
                    "document_id": doc_id,
                    "risk_terms": list(set(found_risks)),
                    "contexts": risk_contexts[:3]  # Top 3 contexts
                })
    
    return risk_signals


def synthesize_with_llm(
    per_document_summaries: List[Dict[str, Any]],
    rag_insights: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Use LLM to synthesize cross-document insights.
    Only called when LLM is enabled - RAG insights still returned if LLM fails.
    
    Args:
        per_document_summaries: List of document summaries
        rag_insights: RAG-extracted insights (themes, overlaps, etc.)
        
    Returns:
        Enhanced insights with LLM synthesis
    """
    # Build prompt from RAG insights
    summaries_text = "\n\n".join([
        f"Document {i+1} ({s['document_id']}):\n{s['summary']}"
        for i, s in enumerate(per_document_summaries)
    ])
    
    themes_text = "\n".join([
        f"- {theme['theme']} (appears in {theme['frequency']} documents)"
        for theme in rag_insights.get('overlaps', [])[:5]
    ])
    
    prompt = f"""Analyze the following document summaries and extracted themes to provide cross-document insights.

DOCUMENT SUMMARIES:
{summaries_text}

EXTRACTED OVERLAPPING THEMES:
{themes_text}

Based ONLY on the information above, provide:
1. A brief synthesis of the main cross-document themes (2-3 sentences)
2. Key relationships or patterns you notice
3. Any notable contrasts between documents

Keep your response concise and grounded in the provided summaries. Do not add external information."""
    
    try:
        llm_start = time.time()
        llm_response = call_llm(
            prompt=prompt,
            system="You are a document analyst. Synthesize insights from provided summaries without adding external information.",
            temperature=0.3
        )
        llm_latency = int((time.time() - llm_start) * 1000)
        
        synthesis = llm_response["text"]
        provider = llm_response["provider"]
        
        logger.info(f"LLM synthesis completed using {provider} in {llm_latency}ms")
        
        # Add synthesis to insights
        enhanced_insights = rag_insights.copy()
        enhanced_insights["llm_synthesis"] = synthesis
        enhanced_insights["synthesis_provider"] = provider
        enhanced_insights["synthesis_latency_ms"] = llm_latency
        
        return enhanced_insights
        
    except Exception as e:
        logger.error(f"LLM synthesis failed: {str(e)}, returning RAG-only insights")
        return rag_insights


def aggregate_insights(
    document_ids: List[str],
    mode: str = "auto",
    max_chunks: int = 5
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Aggregate insights across multiple documents.
    
    Process:
    1. Summarize each document individually (Phase B)
    2. Extract RAG-based cross-document insights
    3. Optionally synthesize with LLM (if enabled and mode allows)
    
    Args:
        document_ids: List of document IDs to analyze
        mode: Summarization mode for individual docs (auto/extractive/hybrid)
        max_chunks: Max chunks per document for summarization
        
    Returns:
        Tuple of (result_dict, telemetry_dict)
        
    Raises:
        ValueError: If fewer than 2 documents provided
    """
    start_time = time.time()
    
    # Validate input
    if not document_ids or len(document_ids) < MIN_DOCUMENTS_FOR_AGGREGATION:
        raise ValueError(
            f"Need at least {MIN_DOCUMENTS_FOR_AGGREGATION} documents for aggregation. "
            f"Received {len(document_ids) if document_ids else 0}."
        )
    
    logger.info(f"Starting multi-document aggregation - {len(document_ids)} documents, Mode: {mode}")
    
    # Initialize telemetry with all observability fields
    telemetry = {
        "routing": "insight_aggregator",
        "mode_requested": mode,
        "files_requested": len(document_ids),
        "files_processed": 0,
        "files_failed": 0,
        "latency_ms_summarization": 0,
        "latency_ms_aggregation": 0,
        "latency_ms_clustering": 0,
        "latency_ms_total": 0,
        "hybrid_used": False,
        "provider": None,
        "error_class": None,
        # Observability fields (always present)
        "semantic_clustering_used": False,
        "cluster_count": 0,
        "avg_cluster_confidence": None,
        "fallback_reason": None,
        "degradation_level": "none",
        "graceful_message": None,
        "user_action_hint": None,
        "evidence_links_available": False
    }
    
    # Step 1: Summarize each document
    logger.info(f"Phase 1: Per-document summarization - Processing {len(document_ids)} documents")
    summarization_start = time.time()
    
    per_document_summaries = []
    failed_documents = []
    
    for doc_id in document_ids:
        try:
            summary, summary_telemetry = summarize_document(
                document_id=doc_id,
                mode=mode,
                max_chunks=max_chunks
            )
            
            # Check if summary is actually usable (has content and chunks)
            chunks_used = summary_telemetry.get("chunks_used", 0)
            if not summary or not summary.strip() or chunks_used == 0:
                error_msg = "No content found for document"
                logger.warning(f"Document {doc_id} failed: {error_msg} - chunks_used={chunks_used}")
                failed_documents.append({
                    "document_id": doc_id,
                    "error": error_msg
                })
                telemetry["files_failed"] += 1
                continue
            
            per_document_summaries.append({
                "document_id": doc_id,
                "summary": summary,
                "confidence": summary_telemetry.get("confidence_top", 0),
                "mode_used": summary_telemetry.get("mode_used"),
                "chunks_used": chunks_used
            })
            
            telemetry["files_processed"] += 1
            logger.info(f"Document {doc_id} processed successfully - mode={summary_telemetry.get('mode_used')}, chunks={chunks_used}")
            
        except Exception as e:
            logger.error(f"Failed to summarize document {doc_id}: {str(e)}")
            failed_documents.append({
                "document_id": doc_id,
                "error": str(e)
            })
            telemetry["files_failed"] += 1
    
    summarization_latency = int((time.time() - summarization_start) * 1000)
    telemetry["latency_ms_summarization"] = summarization_latency
    logger.info(f"Phase 1 complete - {telemetry['files_processed']} succeeded, {telemetry['files_failed']} failed, {summarization_latency}ms")
    
    # Check if we have enough successful summaries
    if len(per_document_summaries) < MIN_DOCUMENTS_FOR_AGGREGATION:
        error_msg = (
            f"Too few successful summaries ({len(per_document_summaries)}) "
            f"to perform aggregation. Need at least {MIN_DOCUMENTS_FOR_AGGREGATION}."
        )
        logger.error(f"AGGREGATION ABORTED: {error_msg}")
        logger.info(f"Pipeline decision: insufficient_documents_fallback - {len(per_document_summaries)}/{MIN_DOCUMENTS_FOR_AGGREGATION} required")
        
        result = {
            "per_document": per_document_summaries,
            "failed_documents": failed_documents,
            "aggregated_insights": None,
            "message": error_msg
        }
        
        # Add graceful messaging for insufficient documents
        graceful_data = graceful_fallback(
            "insights_all_failed",
            reason=f"{len(per_document_summaries)}_successful_of_{len(document_ids)}_requested",
            meta={"files_requested": len(document_ids), "files_processed": len(per_document_summaries)}
        )
        telemetry.update(graceful_data)
        telemetry["error_class"] = "insufficient_documents"
        telemetry["latency_ms_total"] = int((time.time() - start_time) * 1000)
        
        return result, telemetry
    
    # Step 2: Extract RAG-based cross-document insights
    logger.info(f"Phase 2: Cross-document RAG extraction - Analyzing {len(per_document_summaries)} summaries")
    aggregation_start = time.time()
    
    rag_insights = {
        "themes": extract_key_phrases(
            " ".join([s['summary'] for s in per_document_summaries]),
            top_n=15
        ),
        "overlaps": find_overlapping_themes(per_document_summaries),
        "differences": extract_unique_aspects(per_document_summaries),
        "entities": extract_entities(per_document_summaries),
        "risk_signals": detect_risk_signals(per_document_summaries)
    }
    
    aggregation_latency = int((time.time() - aggregation_start) * 1000)
    telemetry["latency_ms_aggregation"] = aggregation_latency
    logger.info(
        f"Phase 2 complete - themes={len(rag_insights['themes'])}, "
        f"overlaps={len(rag_insights['overlaps'])}, "
        f"entities={len(rag_insights['entities'])}, "
        f"risks={len(rag_insights['risk_signals'])}, "
        f"{aggregation_latency}ms"
    )
    
    # Step 2.5: Semantic clustering enhancement (non-breaking addition)
    logger.info(f"Phase 2.5: Semantic clustering - Attempting to cluster {len(rag_insights['themes'])} themes and {len(rag_insights['overlaps'])} overlaps")
    clustering_start = time.time()
    
    try:
        from app.tools.insights.semantic_clustering import create_semantic_clusters
        
        semantic_clusters, clustering_metadata = create_semantic_clusters(
            themes=rag_insights["themes"],
            overlaps=rag_insights["overlaps"],
            summaries=per_document_summaries
        )
        
        # Add semantic clusters to insights (non-breaking)
        if semantic_clusters:
            rag_insights["semantic_clusters"] = semantic_clusters
            rag_insights["evidence_links"] = clustering_metadata.get("evidence_links_available", False)
        
        # Merge clustering metadata into telemetry
        # These fields are guaranteed to be present from create_semantic_clusters
        telemetry["semantic_clustering_used"] = clustering_metadata.get("semantic_clustering_used", False)
        telemetry["cluster_count"] = clustering_metadata.get("cluster_count", 0)
        telemetry["avg_cluster_confidence"] = clustering_metadata.get("avg_cluster_confidence", None)
        telemetry["evidence_links_available"] = clustering_metadata.get("evidence_links_available", False)
        telemetry["fallback_reason"] = clustering_metadata.get("fallback_reason", None)
        
        clustering_latency = int((time.time() - clustering_start) * 1000)
        telemetry["latency_ms_clustering"] = clustering_latency
        
        # Log detailed clustering outcome
        if clustering_metadata['semantic_clustering_used']:
            logger.info(
                f"Phase 2.5 complete - CLUSTERING SUCCESS - "
                f"clusters={clustering_metadata.get('cluster_count', 0)}, "
                f"avg_confidence={clustering_metadata.get('avg_cluster_confidence', 0):.3f}, "
                f"evidence_available={clustering_metadata.get('evidence_links_available', False)}, "
                f"{clustering_latency}ms"
            )
        else:
            fallback_reason = clustering_metadata.get('fallback_reason', 'unknown')
            logger.info(
                f"Phase 2.5 complete - CLUSTERING FALLBACK - "
                f"reason={fallback_reason}, "
                f"{clustering_latency}ms"
            )
        
    except Exception as e:
        logger.warning(f"Phase 2.5 failed - CLUSTERING ERROR: {type(e).__name__} - {str(e)}")
        logger.info(f"Pipeline decision: semantic_clustering_disabled - Continuing with RAG-only insights")
        telemetry["semantic_clustering_used"] = False
        telemetry["cluster_count"] = 0
        telemetry["clustering_error"] = type(e).__name__
    
    # Step 2.7: Cross-File Semantic Intelligence (NEW UPGRADE)
    logger.info(f"Phase 2.7: Cross-File Analysis - Analyzing {len(per_document_summaries)} document summaries")
    cross_file_start = time.time()
    
    try:
        from app.tools.insights.cross_file_analyzer import analyze_cross_file_semantics, detect_overlapping_concepts
        
        # Perform cross-file semantic analysis
        cross_file_result, cross_file_telemetry = analyze_cross_file_semantics(
            per_document_summaries,
            mode="extractive"  # Default mode, can be overridden if mode="llm_synthesis"
        )
        
        # Add cross-file results to insights (non-breaking)
        if cross_file_telemetry.get("cross_file_analysis_used", False):
            rag_insights["cross_file_semantic_clusters"] = cross_file_result.get("semantic_clusters", [])
            rag_insights["cluster_confidence"] = cross_file_result.get("cluster_confidence")
            rag_insights["cross_file_overlap_detected"] = cross_file_result.get("cross_file_overlap_detected", False)
            rag_insights["shared_themes"] = cross_file_result.get("shared_themes", [])
            
            # Detect specific overlapping concepts
            overlapping_concepts = detect_overlapping_concepts(
                cross_file_result.get("semantic_clusters", []),
                per_document_summaries
            )
            rag_insights["overlapping_concepts"] = overlapping_concepts
        
        # Merge cross-file telemetry
        telemetry["cross_file_analysis_used"] = cross_file_telemetry.get("cross_file_analysis_used", False)
        telemetry["cross_file_cluster_count"] = cross_file_telemetry.get("cluster_count", 0)
        telemetry["cross_file_avg_confidence"] = cross_file_telemetry.get("avg_cluster_confidence")
        telemetry["documents_clustered"] = cross_file_telemetry.get("documents_clustered", 0)
        telemetry["documents_unclustered"] = cross_file_telemetry.get("documents_unclustered", 0)
        telemetry["weak_signals_detected"] = cross_file_telemetry.get("weak_signals_detected", False)
        telemetry["cross_file_fallback_reason"] = cross_file_telemetry.get("fallback_reason")
        
        cross_file_latency = cross_file_telemetry.get("latency_ms", 0)
        telemetry["latency_ms_cross_file"] = cross_file_latency
        
        # Log detailed outcome
        if cross_file_telemetry.get("cross_file_analysis_used", False):
            logger.info(
                f"Phase 2.7 complete - CROSS-FILE SUCCESS - "
                f"clusters={cross_file_telemetry.get('cluster_count', 0)}, "
                f"avg_confidence={cross_file_telemetry.get('avg_cluster_confidence', 0):.3f}, "
                f"docs_clustered={cross_file_telemetry.get('documents_clustered', 0)}/{len(per_document_summaries)}, "
                f"{cross_file_latency}ms"
            )
        else:
            fallback_reason = cross_file_telemetry.get("fallback_reason", "unknown")
            logger.info(
                f"Phase 2.7 complete - CROSS-FILE FALLBACK - "
                f"reason={fallback_reason}, "
                f"{cross_file_latency}ms"
            )
        
    except Exception as e:
        logger.warning(f"Phase 2.7 failed - CROSS-FILE ERROR: {type(e).__name__} - {str(e)}")
        logger.info(f"Pipeline decision: cross_file_analysis_disabled - Continuing with phrase-level insights")
        telemetry["cross_file_analysis_used"] = False
        telemetry["cross_file_cluster_count"] = 0
        telemetry["cross_file_error"] = type(e).__name__
    
    # Step 3: Optional LLM synthesis
    final_insights = rag_insights
    
    if mode in ["auto", "hybrid"] and is_llm_enabled():
        logger.info("Phase 3: LLM synthesis - Enhancing insights with LLM")
        final_insights = synthesize_with_llm(per_document_summaries, rag_insights)
        
        if "synthesis_provider" in final_insights:
            telemetry["hybrid_used"] = True
            telemetry["provider"] = final_insights["synthesis_provider"]
            logger.info(f"Phase 3 complete - LLM synthesis successful using {final_insights['synthesis_provider']}")
        else:
            logger.warning("Phase 3 complete - LLM synthesis failed, using RAG-only insights")
    else:
        logger.info(f"Phase 3 skipped - mode={mode}, llm_enabled={is_llm_enabled()}")
        logger.info("Step 3: Skipping LLM synthesis (mode=extractive or LLM disabled)")
    
    # Build final result
    result = {
        "per_document": per_document_summaries,
        "aggregated_insights": final_insights
    }
    
    if failed_documents:
        result["failed_documents"] = failed_documents
        result["message"] = f"Processed {len(per_document_summaries)} documents successfully, {len(failed_documents)} failed"
        logger.warning(f"Pipeline result: PARTIAL SUCCESS - {len(per_document_summaries)} succeeded, {len(failed_documents)} failed")
        
        # Add graceful messaging for partial failures
        graceful_data = graceful_fallback(
            "insights_partial_failure",
            reason=f"{len(failed_documents)}_of_{len(document_ids)}_failed",
            meta={"files_failed": len(failed_documents)}
        )
        telemetry.update(graceful_data)
    else:
        # Full success
        logger.info(f"Pipeline result: FULL SUCCESS - All {len(per_document_summaries)} documents processed")
        graceful_data = success_message("insights_aggregate", {"files": len(per_document_summaries)})
        telemetry.update(graceful_data)
    
    # Check for clustering fallback
    if not telemetry.get("semantic_clustering_used", False) and telemetry.get("fallback_reason"):
        # Clustering was attempted but fell back - add mild degradation note
        logger.info(f"Pipeline note: Clustering fallback detected - reason={telemetry.get('fallback_reason')} - Adding user-facing note")
        clustering_graceful = graceful_fallback(
            "insights_no_clustering",
            reason=telemetry.get("fallback_reason", "unknown"),
            suggestion="This doesn't affect the core insights—themes and overlaps are still available."
        )
        # Only override if we don't already have a more severe degradation
        if telemetry.get("degradation_level") == "none":
            telemetry["graceful_message"] = clustering_graceful["graceful_message"]
            telemetry["degradation_level"] = "mild"
            telemetry["user_action_hint"] = clustering_graceful["user_action_hint"]
    
    # Finalize telemetry
    total_latency = int((time.time() - start_time) * 1000)
    telemetry["latency_ms_total"] = total_latency
    
    logger.info(
        f"AGGREGATION COMPLETE - "
        f"processed={telemetry['files_processed']}, "
        f"failed={telemetry['files_failed']}, "
        f"total_latency={total_latency}ms, "
        f"hybrid={telemetry['hybrid_used']}, "
        f"clustering={telemetry.get('semantic_clustering_used', False)}, "
        f"degradation={telemetry.get('degradation_level', 'none')}"
    )
    
    # Add narrative format (optional, for export consistency)
    try:
        from app.core.insights.narrative_formatter import convert_to_narrative_insight
        
        # Convert aggregated insights to narrative format
        narrative_insight = convert_to_narrative_insight(
            {
                "theme": f"Aggregated Insights from {len(per_document_summaries)} Documents",
                "evidence": final_insights.get("overlapping_themes", [])[:5],  # Top 5 themes
                "overlaps": final_insights.get("overlapping_themes", []),
                "documents": document_ids,
                "confidence": telemetry.get("confidence_score", 0.5),
                "synthesis_used": telemetry.get("hybrid_used", False)
            },
            source_type="aggregation"
        )
        
        # Add as optional field (non-breaking)
        result["narrative_insight"] = narrative_insight
        telemetry["narrative_format_available"] = True
        
    except Exception as e:
        logger.debug(f"Narrative format conversion skipped: {str(e)}")
        telemetry["narrative_format_available"] = False
    
    # Ensure complete telemetry before returning
    from app.core.telemetry import ensure_complete_telemetry
    telemetry = ensure_complete_telemetry(telemetry)
    
    return result, telemetry
