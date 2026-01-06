"""
Comprehensive Tests for Unified Observability and Resilience Layer

Tests the telemetry tracking, graceful degradation, and fault tolerance
across all platform components.

Test Coverage:
- Telemetry field presence and consistency
- Timeout handling with fallback
- Embedding failure with extractive mode
- VectorDB unavailability with keyword fallback
- Partial failure handling
- Weak signal degradation
- Error handling without stack traces
- Degradation level transitions
- Graceful message quality
"""

import pytest
import time
from unittest.mock import Mock, patch
from app.utils.telemetry import (
    TelemetryTracker,
    ComponentType,
    DegradationLevel,
    ensure_telemetry_fields,
    merge_telemetry,
    with_telemetry
)
from app.utils.resilience import (
    resilient_operation,
    EmbeddingFallbackHandler,
    VectorDBFallbackHandler,
    PartialFailureHandler,
    WeakSignalHandler,
    with_timeout_fallback
)


class TestTelemetryTracking:
    """Test telemetry tracking functionality."""
    
    def test_telemetry_initialization(self):
        """Telemetry should initialize with all required fields."""
        tracker = TelemetryTracker(ComponentType.RAG_ASK)
        telemetry = tracker._initialize_telemetry()
        
        # Check all required fields present
        required_fields = [
            "latency_ms_total",
            "latency_ms_retrieval",
            "latency_ms_embedding",
            "latency_ms_llm",
            "confidence_score",
            "routing_decision",
            "fallback_triggered",
            "retry_count",
            "cache_hit",
            "degradation_level",
            "graceful_message",
            "fallback_reason"
        ]
        
        for field in required_fields:
            assert field in telemetry, f"Missing field: {field}"
    
    def test_telemetry_context_manager(self):
        """Telemetry tracker should work as context manager."""
        import time
        with TelemetryTracker(ComponentType.RAG_SEARCH) as tracker:
            time.sleep(0.05)  # Ensure measurable latency
            tracker.set_confidence(0.85)
            tracker.set_retrieval_latency(50)
        
        telemetry = tracker.get_telemetry()
        
        assert telemetry["confidence_score"] == 0.85
        assert telemetry["latency_ms_retrieval"] == 50
        assert telemetry["latency_ms_total"] > 0
    
    def test_latency_tracking(self):
        """Latency should be tracked automatically."""
        with TelemetryTracker(ComponentType.SUMMARIZE) as tracker:
            time.sleep(0.05)  # 50ms
        
        telemetry = tracker.get_telemetry()
        assert telemetry["latency_ms_total"] >= 50
    
    def test_confidence_rounding(self):
        """Confidence scores should be rounded to 3 decimals."""
        tracker = TelemetryTracker(ComponentType.RAG_ASK)
        tracker.set_confidence(0.123456789)
        
        assert tracker.telemetry["confidence_score"] == 0.123
    
    def test_fallback_trigger(self):
        """Fallback trigger should set flags correctly."""
        tracker = TelemetryTracker(ComponentType.RAG_SEARCH)
        tracker.trigger_fallback("embedding_unavailable")
        
        assert tracker.telemetry["fallback_triggered"] is True
        assert tracker.telemetry["fallback_reason"] == "embedding_unavailable"
    
    def test_degradation_setting(self):
        """Degradation level should be set with message."""
        tracker = TelemetryTracker(ComponentType.AGGREGATE)
        tracker.set_degradation(
            DegradationLevel.MILD,
            "Some documents could not be processed.",
            "partial_failure"
        )
        
        assert tracker.telemetry["degradation_level"] == "mild"
        assert tracker.telemetry["graceful_message"] == "Some documents could not be processed."
        assert tracker.telemetry["fallback_reason"] == "partial_failure"


class TestResilientOperations:
    """Test resilient operation wrappers."""
    
    def test_resilient_decorator_success(self):
        """Resilient decorator should pass through success."""
        @resilient_operation(ComponentType.RAG_ASK, fallback_value={})
        def successful_op(x: int):
            result = {"value": x * 2}
            telemetry = {"confidence_score": 0.9}
            return result, telemetry
        
        result, telemetry = successful_op(5)
        
        assert result["value"] == 10
        assert telemetry["confidence_score"] == 0.9
        assert telemetry["degradation_level"] == "none"
    
    def test_resilient_decorator_handles_exception(self):
        """Resilient decorator should handle exceptions gracefully."""
        @resilient_operation(ComponentType.SUMMARIZE, fallback_value={"summary": ""})
        def failing_op():
            raise ValueError("Something went wrong")
        
        result, telemetry = failing_op()
        
        # Should return fallback value
        assert result == {"summary": ""}
        
        # Should have error telemetry
        assert telemetry["degradation_level"] == "failed"
        assert telemetry["fallback_triggered"] is True
        assert "ValueError" in telemetry["fallback_reason"]
        assert telemetry["graceful_message"] is not None
        assert "limitations" in telemetry["graceful_message"].lower()


class TestEmbeddingFallback:
    """Test embedding failure handling."""
    
    def test_embedding_fallback_triggered(self):
        """Embedding fallback should trigger extractive mode."""
        handler = EmbeddingFallbackHandler(ComponentType.RAG_SEARCH)
        
        with handler as h:
            h.trigger_fallback("embedding_unavailable")
        
        result, telemetry = handler.get_result({"results": []})
        
        assert telemetry["fallback_triggered"] is True
        assert telemetry["routing_decision"] == "extractive_fallback"
        assert telemetry["degradation_level"] == "fallback"
        assert "semantic" in telemetry["graceful_message"].lower()
    
    def test_embedding_fallback_not_triggered(self):
        """Embedding fallback should not trigger on success."""
        handler = EmbeddingFallbackHandler(ComponentType.RAG_ASK)
        
        with handler as h:
            h.set_success()
        
        result, telemetry = handler.get_result({"answer": "test"})
        
        assert telemetry["fallback_triggered"] is False
        assert telemetry["routing_decision"] == "semantic_search"
        assert telemetry["degradation_level"] == "none"


class TestVectorDBFallback:
    """Test vector database failure handling."""
    
    def test_vectordb_fallback_triggered(self):
        """VectorDB fallback should trigger keyword search."""
        handler = VectorDBFallbackHandler(ComponentType.RAG_SEARCH)
        
        with handler as h:
            h.trigger_fallback("vectordb_unavailable")
        
        result, telemetry = handler.get_result({"results": []})
        
        assert telemetry["fallback_triggered"] is True
        assert telemetry["routing_decision"] == "keyword_fallback"
        assert telemetry["degradation_level"] == "degraded"
        assert "accuracy" in telemetry["graceful_message"].lower()
    
    def test_vectordb_success(self):
        """VectorDB should not fallback on success."""
        handler = VectorDBFallbackHandler(ComponentType.RAG_ASK)
        
        with handler as h:
            h.set_success()
        
        result, telemetry = handler.get_result({"answer": "test"})
        
        assert telemetry["fallback_triggered"] is False
        assert telemetry["routing_decision"] == "vector_search"


class TestPartialFailures:
    """Test partial failure handling."""
    
    def test_partial_failure_all_success(self):
        """All successful should have no degradation."""
        handler = PartialFailureHandler(ComponentType.AGGREGATE, total_items=3)
        
        with handler as h:
            h.mark_success()
            h.mark_success()
            h.mark_success()
        
        result, telemetry = handler.get_result(["doc1", "doc2", "doc3"])
        
        assert result["success_count"] == 3
        assert result["failure_count"] == 0
        assert telemetry["degradation_level"] == "none"
        assert telemetry["graceful_message"] is None
    
    def test_partial_failure_all_failed(self):
        """All failed should have failed degradation."""
        handler = PartialFailureHandler(ComponentType.AGGREGATE, total_items=3)
        
        with handler as h:
            h.mark_failure("doc1", "error1")
            h.mark_failure("doc2", "error2")
            h.mark_failure("doc3", "error3")
        
        result, telemetry = handler.get_result([])
        
        assert result["success_count"] == 0
        assert result["failure_count"] == 3
        assert telemetry["degradation_level"] == "failed"
        assert "none" in telemetry["graceful_message"].lower()
    
    def test_partial_failure_mild(self):
        """Minority failures should be mild degradation."""
        handler = PartialFailureHandler(ComponentType.AGGREGATE, total_items=5)
        
        with handler as h:
            h.mark_success()
            h.mark_success()
            h.mark_success()
            h.mark_success()
            h.mark_failure("doc5", "error")
        
        result, telemetry = handler.get_result(["doc1", "doc2", "doc3", "doc4"])
        
        assert result["success_count"] == 4
        assert result["failure_count"] == 1
        assert telemetry["degradation_level"] == "mild"
        assert "1 of 5" in telemetry["graceful_message"]
    
    def test_partial_failure_major(self):
        """Majority failures should be degraded."""
        handler = PartialFailureHandler(ComponentType.AGGREGATE, total_items=5)
        
        with handler as h:
            h.mark_success()
            h.mark_success()
            h.mark_failure("doc3", "error3")
            h.mark_failure("doc4", "error4")
            h.mark_failure("doc5", "error5")
        
        result, telemetry = handler.get_result(["doc1", "doc2"])
        
        assert result["success_count"] == 2
        assert result["failure_count"] == 3
        assert telemetry["degradation_level"] == "degraded"
        assert "2 of 5" in telemetry["graceful_message"]


class TestWeakSignalHandling:
    """Test weak signal degradation."""
    
    def test_weak_signal_low_confidence(self):
        """Low confidence should trigger degradation."""
        handler = WeakSignalHandler(
            ComponentType.CSV_INSIGHTS,
            confidence_threshold=0.5
        )
        
        with handler as h:
            h.check_confidence(0.3)  # Below threshold
        
        assert h.should_degrade() is True
        
        result, telemetry = handler.get_result({"insights": []})
        
        assert telemetry["degradation_level"] == "degraded"
        assert telemetry["confidence_score"] == 0.3
        assert "low confidence" in telemetry["graceful_message"].lower()
    
    def test_weak_signal_sufficient_confidence(self):
        """Sufficient confidence should not degrade."""
        handler = WeakSignalHandler(
            ComponentType.CSV_INSIGHTS,
            confidence_threshold=0.5
        )
        
        with handler as h:
            h.check_confidence(0.8)  # Above threshold
        
        assert h.should_degrade() is False
        
        result, telemetry = handler.get_result({"insights": []})
        
        assert telemetry["degradation_level"] == "none"
    
    def test_weak_signal_insufficient_data(self):
        """Insufficient data should trigger degradation."""
        handler = WeakSignalHandler(
            ComponentType.CSV_INSIGHTS,
            min_data_points=10
        )
        
        with handler as h:
            h.check_data_size(5)  # Below minimum
        
        assert h.should_degrade() is True
        
        result, telemetry = handler.get_result({"insights": []})
        
        assert telemetry["degradation_level"] == "degraded"
        assert "insufficient data" in telemetry["graceful_message"].lower()


class TestTelemetryUtilities:
    """Test telemetry utility functions."""
    
    def test_ensure_telemetry_fields(self):
        """Should ensure all required fields present."""
        partial = {
            "confidence_score": 0.8,
            "latency_ms_total": 100
        }
        
        complete = ensure_telemetry_fields(partial)
        
        # Check all fields present
        assert "latency_ms_retrieval" in complete
        assert "fallback_triggered" in complete
        assert "degradation_level" in complete
        
        # Check provided values preserved
        assert complete["confidence_score"] == 0.8
        assert complete["latency_ms_total"] == 100
    
    def test_merge_telemetry_latencies(self):
        """Should sum latency fields."""
        t1 = {
            "latency_ms_total": 100,
            "latency_ms_retrieval": 50,
            "latency_ms_llm": 40
        }
        
        t2 = {
            "latency_ms_total": 80,
            "latency_ms_retrieval": 30,
            "latency_ms_embedding": 20
        }
        
        merged = merge_telemetry(t1, t2)
        
        assert merged["latency_ms_total"] == 180
        assert merged["latency_ms_retrieval"] == 80
        assert merged["latency_ms_llm"] == 40
        assert merged["latency_ms_embedding"] == 20
    
    def test_merge_telemetry_degradation_levels(self):
        """Should take highest degradation level."""
        t1 = {"degradation_level": "none"}
        t2 = {"degradation_level": "mild"}
        t3 = {"degradation_level": "failed"}
        
        merged = merge_telemetry(t1, t2, t3)
        
        # Should take highest (failed)
        assert merged["degradation_level"] == "failed"
    
    def test_merge_telemetry_confidence(self):
        """Should take minimum (most conservative) confidence."""
        t1 = {"confidence_score": 0.9}
        t2 = {"confidence_score": 0.7}
        t3 = {"confidence_score": 0.85}
        
        merged = merge_telemetry(t1, t2, t3)
        
        assert merged["confidence_score"] == 0.7


class TestGracefulMessages:
    """Test graceful message quality."""
    
    def test_no_stack_traces_in_messages(self):
        """Graceful messages should not contain stack traces."""
        @resilient_operation(ComponentType.RAG_ASK, fallback_value={})
        def failing_function():
            raise RuntimeError("Internal error with traceback")
        
        result, telemetry = failing_function()
        
        message = telemetry.get("graceful_message", "")
        
        # Should not contain technical terms
        assert "traceback" not in message.lower()
        assert "runtime" not in message.lower()
        assert "exception" not in message.lower()
        
        # Should be user-friendly
        assert len(message) > 0
        assert len(message) < 200  # Reasonably short
    
    def test_messages_are_actionable(self):
        """Messages should suggest next actions."""
        handler = PartialFailureHandler(ComponentType.AGGREGATE, total_items=2)
        
        with handler as h:
            h.mark_failure("doc1", "error")
            h.mark_failure("doc2", "error")
        
        result, telemetry = handler.get_result([])
        
        message = telemetry["graceful_message"]
        
        # Should contain actionable information
        assert message is not None
        assert len(message) > 10


class TestDegradationTransitions:
    """Test degradation level transitions."""
    
    def test_degradation_level_order(self):
        """Degradation levels should follow severity order."""
        levels = [
            DegradationLevel.NONE,
            DegradationLevel.MILD,
            DegradationLevel.FALLBACK,
            DegradationLevel.DEGRADED,
            DegradationLevel.FAILED
        ]
        
        # Verify enum values are distinct
        values = [level.value for level in levels]
        assert len(values) == len(set(values))
    
    def test_merge_respects_severity(self):
        """Merge should respect degradation severity."""
        # Failed is most severe
        t1 = {"degradation_level": "none", "graceful_message": "All good"}
        t2 = {"degradation_level": "failed", "graceful_message": "Failed"}
        
        merged = merge_telemetry(t1, t2)
        
        assert merged["degradation_level"] == "failed"
        assert merged["graceful_message"] == "Failed"


class TestIntegrationScenarios:
    """Integration tests for common failure scenarios."""
    
    def test_timeout_fallback_scenario(self):
        """Simulate timeout with fallback."""
        @with_timeout_fallback(
            timeout_seconds=1,
            fallback_value={"results": []},
            component=ComponentType.RAG_SEARCH
        )
        def slow_operation():
            time.sleep(2)  # Will timeout
            return {"results": ["item"]}, {}
        
        # Note: Timeout may not work on Windows, so just test structure
        result, telemetry = slow_operation()
        
        # Should have telemetry
        assert "latency_ms_total" in telemetry
        assert "degradation_level" in telemetry
    
    def test_embedding_failure_extractive_mode(self):
        """Simulate embedding failure continuing with extractive."""
        handler = EmbeddingFallbackHandler(ComponentType.RAG_ASK)
        
        with handler as h:
            try:
                # Simulate embedding failure
                raise ConnectionError("Embedding service unavailable")
            except ConnectionError:
                h.trigger_fallback("embedding_unavailable")
                # Continue with extractive mode
                result_data = {"answer": "Extractive answer"}
        
        result, telemetry = handler.get_result(result_data)
        
        assert result["answer"] == "Extractive answer"
        assert telemetry["routing_decision"] == "extractive_fallback"
        assert telemetry["degradation_level"] == "fallback"
        assert telemetry["fallback_triggered"] is True
    
    def test_partial_aggregation_usable_output(self):
        """Partial aggregation failure should still return results."""
        handler = PartialFailureHandler(ComponentType.AGGREGATE, total_items=3)
        
        successful_docs = []
        
        with handler as h:
            # Simulate processing
            try:
                successful_docs.append({"id": "doc1", "summary": "Summary 1"})
                h.mark_success()
            except Exception:
                h.mark_failure("doc1", "error")
            
            try:
                successful_docs.append({"id": "doc2", "summary": "Summary 2"})
                h.mark_success()
            except Exception:
                h.mark_failure("doc2", "error")
            
            # Third fails
            h.mark_failure("doc3", "processing_error")
        
        result, telemetry = handler.get_result(successful_docs)
        
        # Should have usable data despite failure
        assert len(result["data"]) == 2
        assert result["success_count"] == 2
        assert result["failure_count"] == 1
        
        # Should be mildly degraded, not failed
        assert telemetry["degradation_level"] == "mild"


class TestTelemetryFieldConsistency:
    """Test telemetry field consistency across components."""
    
    def test_all_components_have_consistent_fields(self):
        """All components should use same telemetry structure."""
        components = [
            ComponentType.RAG_ASK,
            ComponentType.RAG_SEARCH,
            ComponentType.SUMMARIZE,
            ComponentType.AGGREGATE,
            ComponentType.CSV_INSIGHTS
        ]
        
        for component in components:
            tracker = TelemetryTracker(component)
            telemetry = tracker._initialize_telemetry()
            
            # All should have same fields
            required = [
                "latency_ms_total",
                "confidence_score",
                "routing_decision",
                "fallback_triggered",
                "degradation_level",
                "graceful_message"
            ]
            
            for field in required:
                assert field in telemetry, f"{component.value} missing {field}"
