"""
Unit tests for graceful messaging layer.

Tests that graceful_response utilities properly add human-friendly messages
to various failure/degradation scenarios while preserving metadata.
"""

import pytest
from app.utils.graceful_response import (
    success_message,
    graceful_fallback,
    graceful_failure,
    add_graceful_context,
    DegradationLevel
)


class TestSuccessMessage:
    """Test success_message function."""
    
    def test_success_no_message(self):
        """Success should return no message, degradation_level=none."""
        result = success_message("rag_search")
        
        assert result["graceful_message"] is None
        assert result["degradation_level"] == "none"
        assert result["user_action_hint"] is None
    
    def test_success_with_details(self):
        """Success can include additional details."""
        result = success_message("rag_search", {"results": 5, "confidence": 0.9})
        
        assert result["graceful_message"] is None
        assert result["degradation_level"] == "none"
        assert result["results"] == 5
        assert result["confidence"] == 0.9


class TestGracefulFallback:
    """Test graceful_fallback function."""
    
    def test_rag_low_confidence(self):
        """Low confidence RAG should return appropriate message."""
        result = graceful_fallback(
            "rag_low_confidence",
            reason="max_similarity=0.45",
            meta={"confidence_top": 0.45}
        )
        
        assert "couldn't find a confident answer" in result["graceful_message"]
        assert result["degradation_level"] == "fallback"
        assert "rephras" in result["user_action_hint"].lower()
        assert result["fallback_reason"] == "max_similarity=0.45"
        assert result["confidence_top"] == 0.45
    
    def test_rag_no_results(self):
        """No results should return appropriate message."""
        result = graceful_fallback("rag_no_results", reason="search_returned_empty")
        
        assert "couldn't find information" in result["graceful_message"]
        assert result["degradation_level"] == "fallback"
        assert "rephras" in result["user_action_hint"].lower() or "keywords" in result["user_action_hint"].lower()
        assert result["fallback_reason"] == "search_returned_empty"
    
    def test_summarize_too_short(self):
        """Too short document should return appropriate message."""
        result = graceful_fallback("summarize_too_short", reason="only_2_chunks")
        
        assert "too small" in result["graceful_message"].lower()
        assert result["degradation_level"] == "fallback"
        assert "longer document" in result["user_action_hint"].lower()
    
    def test_insights_no_clustering(self):
        """No clustering should return appropriate message."""
        result = graceful_fallback(
            "insights_no_clustering",
            reason="embedding_unavailable"
        )
        
        assert "without semantic grouping" in result["graceful_message"]
        assert result["degradation_level"] == "fallback"
        assert "core insights" in result["user_action_hint"].lower()
    
    def test_custom_suggestion(self):
        """Custom suggestion should override default."""
        custom_hint = "Try uploading different documents."
        result = graceful_fallback(
            "rag_low_confidence",
            reason="test",
            suggestion=custom_hint
        )
        
        assert result["user_action_hint"] == custom_hint
    
    def test_unknown_context_fallback(self):
        """Unknown context should use generic message."""
        result = graceful_fallback("unknown_context_123", reason="test")
        
        assert "limitation" in result["graceful_message"].lower()
        assert result["degradation_level"] == "fallback"
        assert result["user_action_hint"] is not None


class TestGracefulFailure:
    """Test graceful_failure function."""
    
    def test_rag_retrieval_error(self):
        """Retrieval error should return appropriate message."""
        result = graceful_failure(
            "rag_retrieval_error",
            error="ChromaDB connection timeout"
        )
        
        assert "issue searching" in result["graceful_message"].lower()
        assert result["degradation_level"] == "failed"
        assert "try again" in result["user_action_hint"].lower()
        assert "error_type" in result
    
    def test_error_not_exposed_to_user(self):
        """Internal error details should not be in graceful_message."""
        internal_error = "NullPointerException at line 42 in module xyz"
        result = graceful_failure("rag_retrieval_error", error=internal_error)
        
        # Message should be generic, not expose internal details
        assert "NullPointerException" not in result["graceful_message"]
        assert "line 42" not in result["graceful_message"]
        assert "module xyz" not in result["graceful_message"]
    
    def test_generic_error(self):
        """Unknown error context should use generic message."""
        result = graceful_failure("unknown_error_type", error="Something bad happened")
        
        assert "issue" in result["graceful_message"].lower() or "error" in result["graceful_message"].lower()
        assert result["degradation_level"] == "failed"


class TestAddGracefulContext:
    """Test add_graceful_context helper."""
    
    def test_merge_graceful_data(self):
        """Should merge graceful data into existing response."""
        response = {
            "answer": "Machine learning is...",
            "confidence": 0.85,
            "chunks": 5
        }
        
        graceful_data = success_message("rag_search")
        
        result = add_graceful_context(response, graceful_data)
        
        # Original data preserved
        assert result["answer"] == "Machine learning is..."
        assert result["confidence"] == 0.85
        assert result["chunks"] == 5
        
        # Graceful fields added
        assert "graceful_message" in result
        assert "degradation_level" in result
        assert result["degradation_level"] == "none"
    
    def test_merge_with_fallback(self):
        """Should merge fallback data into existing response."""
        response = {"results": [], "query_time_ms": 42}
        
        graceful_data = graceful_fallback(
            "rag_no_results",
            reason="empty_collection"
        )
        
        result = add_graceful_context(response, graceful_data)
        
        # Original data preserved
        assert result["results"] == []
        assert result["query_time_ms"] == 42
        
        # Graceful fields added
        assert result["graceful_message"] is not None
        assert result["degradation_level"] == "fallback"
        assert result["user_action_hint"] is not None
        assert result["fallback_reason"] == "empty_collection"


class TestDegradationLevel:
    """Test DegradationLevel enum."""
    
    def test_enum_values(self):
        """Verify all expected degradation levels exist."""
        assert DegradationLevel.NONE.value == "none"
        assert DegradationLevel.MILD.value == "mild"
        assert DegradationLevel.FALLBACK.value == "fallback"
        assert DegradationLevel.DEGRADED.value == "degraded"
        assert DegradationLevel.FAILED.value == "failed"


class TestMessageProperties:
    """Test general properties of graceful messages."""
    
    def test_messages_are_short(self):
        """Messages should be concise (typically 1-2 sentences)."""
        contexts = [
            "rag_low_confidence",
            "rag_no_results",
            "summarize_too_short",
            "insights_no_clustering"
        ]
        
        for context in contexts:
            result = graceful_fallback(context, reason="test")
            message = result["graceful_message"]
            
            # Should be concise
            assert len(message) < 200, f"{context} message too long: {len(message)} chars"
            
            # Should not have multiple paragraphs
            assert message.count("\n\n") == 0, f"{context} has multiple paragraphs"
    
    def test_messages_non_technical(self):
        """Messages should not contain technical jargon."""
        technical_terms = [
            "exception", "null", "stack trace", "embedding", "vector",
            "chromadb", "telemetry", "similarity threshold"
        ]
        
        contexts = [
            "rag_low_confidence",
            "rag_no_results",
            "summarize_too_short"
        ]
        
        for context in contexts:
            result = graceful_fallback(context, reason="test")
            message = result["graceful_message"].lower()
            
            for term in technical_terms:
                assert term not in message, f"{context} contains technical term: {term}"
    
    def test_messages_dont_blame_user(self):
        """Messages should not blame the user."""
        blame_phrases = [
            "you did", "your fault", "you should have", "you forgot",
            "incorrect input", "invalid request", "user error"
        ]
        
        contexts = [
            "rag_low_confidence",
            "rag_no_results",
            "summarize_too_short",
            "insights_partial_failure"
        ]
        
        for context in contexts:
            result = graceful_fallback(context, reason="test")
            message = result["graceful_message"].lower()
            hint = result["user_action_hint"].lower()
            
            for phrase in blame_phrases:
                assert phrase not in message, f"{context} message blames user: {phrase}"
                assert phrase not in hint, f"{context} hint blames user: {phrase}"
    
    def test_action_hints_are_constructive(self):
        """Action hints should suggest next steps."""
        contexts = [
            "rag_low_confidence",
            "rag_no_results",
            "summarize_too_short"
        ]
        
        for context in contexts:
            result = graceful_fallback(context, reason="test")
            hint = result["user_action_hint"]
            
            # Should not be empty
            assert hint is not None and len(hint) > 0
            
            # Should suggest action
            action_words = ["try", "upload", "ensure", "check", "consider", "use"]
            has_action = any(word in hint.lower() for word in action_words)
            assert has_action, f"{context} hint lacks actionable suggestion: {hint}"


class TestMetadataPreservation:
    """Test that metadata is always preserved."""
    
    def test_fallback_preserves_metadata(self):
        """Fallback should preserve all passed metadata."""
        meta = {
            "confidence_top": 0.45,
            "retrieval_pass": "primary",
            "top_k_scores": [0.45, 0.42, 0.38],
            "latency_ms": 150
        }
        
        result = graceful_fallback("rag_low_confidence", reason="test", meta=meta)
        
        # All metadata should be preserved
        assert result["confidence_top"] == 0.45
        assert result["retrieval_pass"] == "primary"
        assert result["top_k_scores"] == [0.45, 0.42, 0.38]
        assert result["latency_ms"] == 150
        
        # Plus graceful fields
        assert "graceful_message" in result
        assert "degradation_level" in result
    
    def test_failure_preserves_metadata(self):
        """Failure should preserve all passed metadata."""
        meta = {
            "attempted_operation": "vector_search",
            "latency_ms": 50,
            "retry_count": 3
        }
        
        result = graceful_failure("rag_retrieval_error", error="timeout", meta=meta)
        
        # All metadata should be preserved
        assert result["attempted_operation"] == "vector_search"
        assert result["latency_ms"] == 50
        assert result["retry_count"] == 3


if __name__ == "__main__":
    print("Running graceful messaging tests...")
    pytest.main([__file__, "-v"])
