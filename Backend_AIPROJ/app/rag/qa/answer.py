import os
import hashlib
import time
from typing import List, Dict, Optional, Tuple
from app.core.logging import setup_logger
from app.core.config import settings
from app.core.cache import get_rag_cache, generate_cache_key as gen_cache_key
from app.llm.router import call_llm, is_llm_enabled

logger = setup_logger("INFO")

# Confidence threshold for retrieval
CONFIDENCE_THRESHOLD = settings.CONFIDENCE_THRESHOLD

# Safe mode options
SAFE_MODE_STRICT = "strict"  # Return no answer when confidence is low
SAFE_MODE_HYBRID = "hybrid"  # Call LLM to infer from chunks when confidence is low

# Factual question keywords for extractive mode
FACTUAL_KEYWORDS = [
    "who", "what", "when", "where", "which", "name", "title", 
    "profession", "job", "role", "date", "time", "age", "phone", 
    "email", "address", "price", "cost"
]


def is_factual_question(question: str) -> bool:
    """
    Determine if a question is factual/lookup-style.
    
    Args:
        question: The question text
        
    Returns:
        bool: True if the question appears to be factual
    """
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in FACTUAL_KEYWORDS)


def is_reasoning_question(question: str) -> bool:
    """
    Determine if a question requires reasoning/synthesis.
    
    Args:
        question: The question text
        
    Returns:
        bool: True if the question requires LLM reasoning
    """
    reasoning_keywords = ["explain", "why", "how", "summarize", "analyze", "compare", "describe", "discuss"]
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in reasoning_keywords)


def generate_cache_key_for_answer(question: str, source: Optional[str] = None) -> str:
    """
    Generate a cache key from question and source.
    
    Args:
        question: The question text
        source: Optional source identifier
        
    Returns:
        str: Cache key hash
    """
    cache_str = f"answer:{question.lower().strip()}|{source or 'default'}"
    return gen_cache_key(cache_str)


def build_context(results: List[Dict]) -> str:
    """
    Build a context string from retrieved chunks.
    
    Args:
        results: List of search results with chunk text and metadata
    
    Returns:
        Formatted context string
    """
    context_parts = []
    
    for idx, result in enumerate(results, start=1):
        chunk_text = result.get("chunk", "")
        score = result.get("score", 0)
        
        # Try to get metadata if available
        metadata_str = ""
        if "metadata" in result:
            metadata = result["metadata"]
            page = metadata.get("page")
            source = metadata.get("source")
            if page and source:
                metadata_str = f" [Source: {source}, Page: {page}]"
            elif source:
                metadata_str = f" [Source: {source}]"
        
        context_parts.append(f"[{idx}]{metadata_str}: {chunk_text}")
    
    return "\n\n".join(context_parts)


def generate_answer(question: str, results: List[Dict], retrieval_telemetry: Optional[Dict] = None) -> Tuple[Dict, Dict]:
    """
    Generate an answer to a question using retrieved context and an LLM.
    
    Args:
        question: The question to answer
        results: List of retrieved chunks with metadata
        retrieval_telemetry: Optional telemetry from retrieval layer
    
    Returns:
        Tuple of (answer_dict, telemetry_dict):
            answer_dict: Dictionary with answer, citations, and chunk count
            telemetry_dict: Dictionary with latency, cache hit, error info
    
    Raises:
        ValueError: If no results provided or no API key configured
        Exception: If LLM API call fails
    """
    # Start latency timer
    start_time = time.time()
    
    # Initialize telemetry
    telemetry = {
        "latency_ms_llm": 0,
        "cache_hit": False,
        "error_class": None,
        "retry_count": 0,
        "mode": "unknown",
        "confidence_path": None,  # Semantic: high_confidence_direct | low_confidence_hybrid | no_signal_in_document | insufficient_evidence
        "answer_status": None,  # Outcome: confident_answer | uncertain_answer | no_answer_in_document | not_enough_confidence_to_answer
        "retrieval_score_primary": None,
        "retrieval_score_fallback": None
    }
    
    # Merge retrieval telemetry if provided
    if retrieval_telemetry:
        telemetry.update({
            "confidence_top": retrieval_telemetry.get("confidence_top"),
            "confidence_threshold": retrieval_telemetry.get("confidence_threshold"),
            "confidence_decision": retrieval_telemetry.get("confidence_decision"),
            "retrieval_pass": retrieval_telemetry.get("retrieval_pass"),
            "top_k_scores": retrieval_telemetry.get("top_k_scores"),
            "latency_ms_retrieval": retrieval_telemetry.get("latency_ms_retrieval")
        })
        # Extract primary score for transparency
        if telemetry.get("confidence_top") is not None:
            telemetry["retrieval_score_primary"] = telemetry["confidence_top"]
    
    if not results:
        telemetry["error_class"] = "NO_RESULTS"
        telemetry["mode"] = "safe_none"
        raise ValueError("No context provided for answer generation")
    
    num_chunks = len(results)
    
    # Extract source from first result for cache key
    source = None
    if results and "metadata" in results[0]:
        source = results[0]["metadata"].get("source")
    
    # Get cache
    answer_cache = get_rag_cache()
    
    # Check cache first
    cache_key = generate_cache_key_for_answer(question, source)
    cached_answer = answer_cache.get(cache_key)
    
    if cached_answer:
        logger.info(f"cache_status=hit mode=cache confidence_path=high_confidence_direct answer_status=confident_answer")
        telemetry["cache_hit"] = True
        telemetry["mode"] = "cache"
        telemetry["confidence_path"] = "high_confidence_direct"
        telemetry["answer_status"] = "confident_answer"
        telemetry["latency_ms_llm"] = int((time.time() - start_time) * 1000)
        
        return cached_answer, telemetry
    
    logger.info(f"cache_status=miss")
    
    # Check confidence score of top result
    top_score = results[0].get("score", 0) if results else 0
    logger.info(f"Top chunk similarity score: {top_score:.3f}")
    
    # Get safe mode from settings
    safe_mode = settings.RAG_SAFE_MODE
    
    if top_score < CONFIDENCE_THRESHOLD:
        logger.info(f"Low confidence score ({top_score:.3f} < {CONFIDENCE_THRESHOLD})")
        
        # STRICT mode: return no answer
        if safe_mode == SAFE_MODE_STRICT:
            logger.info(f"SAFE_MODE_STRICT: returning no answer mode=safe_fallback confidence_path=insufficient_evidence answer_status=not_enough_confidence_to_answer")
            telemetry["mode"] = "safe_fallback"
            telemetry["confidence_path"] = "insufficient_evidence"
            telemetry["answer_status"] = "not_enough_confidence_to_answer"
            telemetry["error_class"] = "RETRIEVAL_WEAK_SIGNAL"
            telemetry["latency_ms_llm"] = int((time.time() - start_time) * 1000)
            
            result = {
                "answer": "No relevant information found in the document.",
                "user_message": "I couldn't find enough relevant information in the document to confidently answer your question.",
                "citations": [],
                "used_chunks": 0
            }
            
            # Ensure complete telemetry before returning
            from app.core.telemetry import ensure_complete_telemetry
            telemetry = ensure_complete_telemetry(telemetry)
            telemetry["latency_ms_total"] = telemetry.get("latency_ms_llm", 0) + telemetry.get("latency_ms_retrieval", 0)
            
            return result, telemetry
        
        # HYBRID mode: try to use LLM to infer from chunks
        if safe_mode == SAFE_MODE_HYBRID and is_llm_enabled():
            logger.info(f"SAFE_MODE_HYBRID: attempting LLM inference on low-confidence chunks confidence_path=low_confidence_hybrid")
            telemetry["mode"] = "rag_llm_hybrid"
            telemetry["confidence_path"] = "low_confidence_hybrid"
            
            try:
                # Build context from retrieved chunks
                context = build_context(results)
                
                # Build prompt for LLM inference
                prompt = f"""I have retrieved the following text chunks from a document, but their similarity to the user's question is below the confidence threshold ({CONFIDENCE_THRESHOLD}).

Retrieved chunks:
{context}

User's question: {question}

Please analyze these chunks carefully and:
1. If they contain ANY relevant information that could help answer the question, provide the best possible answer based on what's available.
2. If the chunks are completely unrelated or don't contain useful information, clearly state that no relevant information was found.

Answer:"""
                
                # Call LLM using unified router
                logger.info("Calling LLM via router for low-confidence inference")
                llm_start = time.time()
                
                llm_response = call_llm(
                    prompt=prompt,
                    system="You are a helpful assistant that carefully analyzes retrieved text to answer questions, even when similarity scores are low. Be honest if the information is not relevant.",
                    temperature=0.7
                )
                
                llm_latency_ms = int((time.time() - llm_start) * 1000)
                telemetry["latency_ms_llm"] = llm_latency_ms
                
                answer_text = llm_response["text"]
                llm_provider = llm_response["provider"]
                telemetry["provider"] = llm_provider
                
                # Extract citations from results
                citations = []
                for idx, result in enumerate(results):
                    try:
                        # Debug log to check score
                        score_value = result.get("score", result.get("relevance_score", 0))
                        if idx == 0:  # Log first result for debugging
                            logger.info(f"First result score: {score_value}, keys: {list(result.keys())}")
                        
                        citation = {
                            "chunk": result.get("chunk", "")[:100] + "...",
                            "score": score_value
                        }
                        if "metadata" in result:
                            metadata = result["metadata"]
                            if "page" in metadata:
                                citation["page"] = metadata["page"]
                            if "source" in metadata:
                                citation["source"] = metadata["source"]
                        citations.append(citation)
                    except Exception as e:
                        logger.warning(f"Failed to extract citation from result: {str(e)}")
                        continue
                
                result = {
                    "answer": answer_text.strip(),
                    "user_message": "This answer is based on weak matches. The document may not clearly contain this information.",
                    "citations": citations,
                    "used_chunks": len(results)
                }
                
                # Set answer status based on content
                if "no relevant information" in answer_text.lower() or "cannot answer" in answer_text.lower():
                    telemetry["answer_status"] = "no_answer_in_document"
                    logger.info(f"answer_status=no_answer_in_document (LLM determined no relevant info)")
                else:
                    telemetry["answer_status"] = "uncertain_answer"
                    logger.info(f"answer_status=uncertain_answer (LLM attempted with weak signal)")
                
                # Cache the result if enabled
                if settings.CACHE_ENABLED:
                    answer_cache.set(cache_key, result)
                    logger.info(f"cache_operation=set mode=rag_llm_hybrid provider={llm_provider}")
                
                return result, telemetry
                
            except Exception as e:
                logger.error(f"LLM inference failed: {str(e)}")
                logger.info(f"Falling back to safe mode mode=safe_fallback confidence_path=insufficient_evidence answer_status=not_enough_confidence_to_answer")
                telemetry["error_class"] = "LLM_PROVIDER_UNAVAILABLE"
                telemetry["mode"] = "safe_fallback"
                telemetry["confidence_path"] = "insufficient_evidence"
                telemetry["answer_status"] = "not_enough_confidence_to_answer"
        
        # Fallback: return no answer (LLM failed or not enabled in HYBRID mode)
        logger.info(f"Returning no answer mode=safe_fallback confidence_path=insufficient_evidence answer_status=not_enough_confidence_to_answer")
        telemetry["mode"] = "safe_fallback"
        telemetry["confidence_path"] = "insufficient_evidence"
        telemetry["answer_status"] = "not_enough_confidence_to_answer"
        telemetry["error_class"] = "RETRIEVAL_WEAK_SIGNAL"
        telemetry["latency_ms_llm"] = int((time.time() - start_time) * 1000)
        
        result = {
            "answer": "No relevant information found in the document.",
            "user_message": "I couldn't find enough relevant information in the document to confidently answer your question.",
            "citations": [],
            "used_chunks": 0
        }
        return result, telemetry
    
    # Extractive mode for factual questions
    if is_factual_question(question) and not is_reasoning_question(question):
        logger.info(f"Using extractive mode for factual question confidence_path=high_confidence_direct answer_status=confident_answer")
        telemetry["mode"] = "rag_confident_extractive"
        telemetry["confidence_path"] = "high_confidence_direct"
        telemetry["answer_status"] = "confident_answer"
        
        # Return the best chunk directly
        best_chunk = results[0].get("chunk", "No information available")
        
        citation = {"chunk": best_chunk[:100] + "..."}
        if "metadata" in results[0]:
            metadata = results[0]["metadata"]
            if "page" in metadata:
                citation["page"] = metadata["page"]
            if "source" in metadata:
                citation["source"] = metadata["source"]
        
        result = {
            "answer": best_chunk,
            "citations": [citation],
            "used_chunks": 1
        }
        
        # Cache the result if enabled
        if settings.CACHE_ENABLED:
            answer_cache.set(cache_key, result)
            logger.info(f"cache_operation=set mode=rag_confident_extractive")
        
        telemetry["latency_ms_llm"] = int((time.time() - start_time) * 1000)
        return result, telemetry
    
    # LLM mode for reasoning or synthesis
    logger.info(f"Using LLM mode for reasoning/synthesis with {num_chunks} chunks")
    
    # Check if LLM is enabled
    if not is_llm_enabled():
        logger.warning("LLM provider not enabled - returning extractive answer confidence_path=high_confidence_direct answer_status=confident_answer")
        telemetry["mode"] = "rag_confident_lightweight"
        telemetry["confidence_path"] = "high_confidence_direct"
        telemetry["answer_status"] = "confident_answer"
        telemetry["error_class"] = "LLM_PROVIDER_UNAVAILABLE"
        
        # Return best chunk directly
        best_chunk = results[0].get("chunk", "No information available")
        
        citation = {"chunk": best_chunk[:100] + "..."}
        if "metadata" in results[0]:
            metadata = results[0]["metadata"]
            if "page" in metadata:
                citation["page"] = metadata["page"]
            if "source" in metadata:
                citation["source"] = metadata["source"]
        
        result = {
            "answer": f"{best_chunk}\n\nNote: LLM provider not enabled — running in lightweight mode.",
            "citations": [citation],
            "used_chunks": 1
        }
        
        # Cache the result if enabled
        if settings.CACHE_ENABLED:
            answer_cache.set(cache_key, result)
            logger.info(f"cache_operation=set mode=rag_confident_lightweight")
        
        telemetry["latency_ms_llm"] = int((time.time() - start_time) * 1000)
        return result, telemetry
    
    try:
        # Build context from retrieved chunks
        context = build_context(results)
        
        # Build prompt
        prompt = f"""Based on the following context, answer the question. If the answer cannot be found in the context, say so.

Context:
{context}

Question: {question}

Answer:"""
        
        # Call LLM using unified router
        logger.info("Calling LLM via router")
        llm_start = time.time()
        
        llm_response = call_llm(
            prompt=prompt,
            system="You are a helpful assistant that answers questions based on the provided context.",
            temperature=0.7
        )
        
        llm_latency_ms = int((time.time() - llm_start) * 1000)
        telemetry["latency_ms_llm"] = llm_latency_ms
        
        answer_text = llm_response["text"]
        llm_provider = llm_response["provider"]
        telemetry["provider"] = llm_provider
        telemetry["mode"] = "rag_confident"
        telemetry["confidence_path"] = "high_confidence_direct"
        telemetry["answer_status"] = "confident_answer"
        
        logger.info(f"LLM response received mode=rag_confident confidence_path=high_confidence_direct answer_status=confident_answer")
        
        # Extract citations from results
        citations = []
        for result in results:
            try:
                citation = {
                    "chunk": result.get("chunk", "")[:100] + "...",
                    "score": result.get("score", result.get("relevance_score", 0))
                }
                if "metadata" in result:
                    metadata = result["metadata"]
                    if "page" in metadata:
                        citation["page"] = metadata["page"]
                    if "source" in metadata:
                        citation["source"] = metadata["source"]
                citations.append(citation)
            except Exception as e:
                logger.warning(f"Failed to extract citation from result: {str(e)}")
                # Continue with other citations
                continue
        
        result = {
            "answer": answer_text.strip(),
            "citations": citations,
            "used_chunks": num_chunks
        }
        
        # Cache the result if enabled
        if settings.CACHE_ENABLED:
            answer_cache.set(cache_key, result)
            logger.info(f"cache_operation=set mode=rag_confident provider={llm_provider}")
        
        # Ensure complete telemetry before returning
        from app.core.telemetry import ensure_complete_telemetry
        telemetry = ensure_complete_telemetry(telemetry)
        telemetry["latency_ms_total"] = telemetry.get("latency_ms_llm", 0) + telemetry.get("latency_ms_retrieval", 0)
        
        return result, telemetry
        
    except ValueError:
        # Re-raise validation errors as-is
        raise
    except Exception as e:
        logger.error(f"Failed to generate answer: {str(e)} confidence_path=insufficient_evidence answer_status=not_enough_confidence_to_answer")
        telemetry["error_class"] = "LLM_PROVIDER_UNAVAILABLE"
        telemetry["confidence_path"] = "insufficient_evidence"
        telemetry["answer_status"] = "not_enough_confidence_to_answer"
        telemetry["latency_ms_llm"] = int((time.time() - start_time) * 1000)
        
        # Ensure complete telemetry before raising
        from app.core.telemetry import ensure_complete_telemetry
        telemetry = ensure_complete_telemetry(telemetry)
        telemetry["latency_ms_total"] = telemetry.get("latency_ms_llm", 0) + telemetry.get("latency_ms_retrieval", 0)
        telemetry["fallback_triggered"] = True
        telemetry["degradation_level"] = "failed"
        
        raise Exception(f"Answer generation failed: {str(e)}")
