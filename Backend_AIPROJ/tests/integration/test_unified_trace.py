"""
Tests for Unified Trace Module — Phase 3

Tests the unified tracing helper module for consistent telemetry.
"""

import pytest
import time
from app.core.telemetry.unified_trace import (
    UnifiedTrace,
    start_trace,
    end_trace,
    record_step,
    attach_metadata,
    finalize_response,
    safe_try,
    ensure_telemetry_fields,
    merge_trace_metadata,
    trace_operation
)


class TestUnifiedTraceLifecycle:
    """Test trace initialization and finalization."""
    
    def test_start_trace_creates_trace_object(self):
        """Test that start_trace creates a UnifiedTrace object."""
        trace = start_trace("test_operation")
        
        assert isinstance(trace, UnifiedTrace)
        assert trace.operation_name == "test_operation"
        assert trace.start_time is not None
        assert trace.end_time is None
        assert trace.success is None
    
    def test_end_trace_finalizes_trace(self):
        """Test that end_trace finalizes a trace."""
        trace = start_trace("test_operation")
        time.sleep(0.01)  # Small delay
        end_trace(trace, success=True)
        
        assert trace.success is True
        assert trace.end_time is not None
        assert trace.metadata["latency_ms_total"] > 0
    
    def test_end_trace_with_error(self):
        """Test that end_trace handles errors."""
        trace = start_trace("test_operation")
        
        try:
            raise ValueError("Test error")
        except Exception as e:
            end_trace(trace, success=False, error=e)
        
        assert trace.success is False
        assert trace.metadata["error_class"] == "ValueError"
    
    def test_trace_latency_calculation(self):
        """Test that latency is calculated correctly."""
        trace = start_trace("test_operation")
        time.sleep(0.05)  # 50ms delay
        end_trace(trace, success=True)
        
        # Should be approximately 50ms
        assert 40 <= trace.metadata["latency_ms_total"] <= 70


class TestTraceStepRecording:
    """Test recording of individual steps."""
    
    def test_record_retrieval_step(self):
        """Test recording a retrieval step."""
        trace = start_trace("test_operation")
        record_step(trace, "retrieval", 25.5)
        
        assert trace.metadata["latency_ms_retrieval"] == 25.5
        assert "retrieval" in trace.steps
        assert trace.steps["retrieval"] == 25.5
    
    def test_record_embedding_step(self):
        """Test recording an embedding step."""
        trace = start_trace("test_operation")
        record_step(trace, "embedding", 15.3)
        
        assert trace.metadata["latency_ms_embedding"] == 15.3
    
    def test_record_llm_step(self):
        """Test recording an LLM step."""
        trace = start_trace("test_operation")
        record_step(trace, "llm", 450.0)
        
        assert trace.metadata["latency_ms_llm"] == 450.0
    
    def test_record_custom_step(self):
        """Test recording a custom step."""
        trace = start_trace("test_operation")
        record_step(trace, "custom_processing", 10.0)
        
        assert "custom_processing" in trace.steps
        assert trace.steps["custom_processing"] == 10.0
    
    def test_multiple_step_recording(self):
        """Test recording multiple steps."""
        trace = start_trace("test_operation")
        record_step(trace, "retrieval", 20.0)
        record_step(trace, "embedding", 15.0)
        record_step(trace, "llm", 100.0)
        
        assert len(trace.steps) == 3
        assert trace.metadata["latency_ms_retrieval"] == 20.0
        assert trace.metadata["latency_ms_embedding"] == 15.0
        assert trace.metadata["latency_ms_llm"] == 100.0


class TestMetadataAttachment:
    """Test attaching metadata to traces."""
    
    def test_attach_routing_decision(self):
        """Test attaching routing decision."""
        trace = start_trace("test_operation")
        attach_metadata(trace, routing_decision="vector_search")
        
        assert trace.metadata["routing_decision"] == "vector_search"
    
    def test_attach_confidence_score(self):
        """Test attaching confidence score."""
        trace = start_trace("test_operation")
        attach_metadata(trace, confidence_score=0.85)
        
        assert trace.metadata["confidence_score"] == 0.85
    
    def test_attach_cache_hit(self):
        """Test attaching cache hit flag."""
        trace = start_trace("test_operation")
        attach_metadata(trace, cache_hit=True)
        
        assert trace.metadata["cache_hit"] is True
    
    def test_attach_multiple_metadata(self):
        """Test attaching multiple metadata fields at once."""
        trace = start_trace("test_operation")
        attach_metadata(
            trace,
            routing_decision="hybrid",
            confidence_score=0.92,
            fallback_triggered=False,
            retry_count=0
        )
        
        assert trace.metadata["routing_decision"] == "hybrid"
        assert trace.metadata["confidence_score"] == 0.92
        assert trace.metadata["fallback_triggered"] is False
        assert trace.metadata["retry_count"] == 0


class TestFinalizeResponse:
    """Test finalizing responses with telemetry."""
    
    def test_finalize_response_basic(self):
        """Test basic response finalization."""
        trace = start_trace("test_operation")
        end_trace(trace, success=True)
        
        response = finalize_response(
            {"answer": "Test answer"},
            trace
        )
        
        assert "answer" in response
        assert "meta" in response
        assert response["meta"]["latency_ms_total"] >= 0
    
    def test_finalize_response_with_degradation(self):
        """Test response finalization with degradation."""
        trace = start_trace("test_operation")
        attach_metadata(trace, degradation_level="fallback")
        end_trace(trace, success=True)
        
        response = finalize_response(
            {"answer": "Fallback answer"},
            trace,
            graceful_message="Using fallback method",
            degradation="fallback"
        )
        
        assert response["meta"]["degradation_level"] == "fallback"
        assert response["meta"]["graceful_message"] == "Using fallback method"
    
    def test_finalize_response_preserves_existing_payload(self):
        """Test that finalization preserves existing payload fields."""
        trace = start_trace("test_operation")
        end_trace(trace, success=True)
        
        original_payload = {
            "answer": "Test",
            "citations": [],
            "confidence": 0.9
        }
        
        response = finalize_response(original_payload, trace)
        
        assert response["answer"] == "Test"
        assert response["citations"] == []
        assert response["confidence"] == 0.9
        assert "meta" in response


class TestSafeTry:
    """Test safe execution with automatic fallback."""
    
    def test_safe_try_successful_execution(self):
        """Test safe_try with successful execution."""
        trace = start_trace("test_operation")
        
        def successful_fn():
            return "success"
        
        result = safe_try(
            "test_step",
            trace,
            successful_fn,
            fallback_value="fallback",
            fallback_message="Should not appear"
        )
        
        assert result == "success"
        assert trace.metadata["fallback_triggered"] is False
    
    def test_safe_try_with_exception_triggers_fallback(self):
        """Test safe_try with exception triggers fallback."""
        trace = start_trace("test_operation")
        
        def failing_fn():
            raise ValueError("Test error")
        
        result = safe_try(
            "test_step",
            trace,
            failing_fn,
            fallback_value="fallback_result",
            fallback_message="Fallback triggered"
        )
        
        assert result == "fallback_result"
        assert trace.metadata["fallback_triggered"] is True
        assert trace.metadata["graceful_message"] == "Fallback triggered"
        assert trace.metadata["degradation_level"] == "fallback"
    
    def test_safe_try_never_raises_to_caller(self):
        """Test that safe_try never raises exceptions to caller."""
        trace = start_trace("test_operation")
        
        def always_fails():
            raise RuntimeError("Critical error")
        
        # Should not raise
        result = safe_try(
            "dangerous_step",
            trace,
            always_fails,
            fallback_value=None,
            fallback_message="Handled gracefully"
        )
        
        assert result is None
        assert trace.metadata["fallback_triggered"] is True
    
    def test_safe_try_with_lambda(self):
        """Test safe_try with lambda functions."""
        trace = start_trace("test_operation")
        
        result = safe_try(
            "lambda_step",
            trace,
            lambda: 10 + 5,
            fallback_value=0,
            fallback_message="Should not appear"
        )
        
        assert result == 15


class TestEnsureTelemetryFields:
    """Test telemetry field validation."""
    
    def test_ensure_fields_adds_missing_fields(self):
        """Test that ensure_telemetry_fields adds missing fields."""
        metadata = {}
        ensure_telemetry_fields(metadata)
        
        assert "latency_ms_total" in metadata
        assert "latency_ms_retrieval" in metadata
        assert "degradation_level" in metadata
        assert "fallback_triggered" in metadata
    
    def test_ensure_fields_preserves_existing_values(self):
        """Test that existing values are preserved."""
        metadata = {
            "latency_ms_total": 100,
            "confidence_score": 0.95
        }
        ensure_telemetry_fields(metadata)
        
        assert metadata["latency_ms_total"] == 100
        assert metadata["confidence_score"] == 0.95
    
    def test_ensure_fields_has_all_required_fields(self):
        """Test that all required fields are present."""
        metadata = {}
        ensure_telemetry_fields(metadata)
        
        required_fields = [
            "latency_ms_total",
            "latency_ms_retrieval",
            "latency_ms_embedding",
            "latency_ms_llm",
            "routing_decision",
            "confidence_score",
            "fallback_triggered",
            "retry_count",
            "cache_hit",
            "degradation_level",
            "graceful_message",
            "error_class"
        ]
        
        for field in required_fields:
            assert field in metadata


class TestMergeTraceMetadata:
    """Test merging of multiple telemetry sources."""
    
    def test_merge_simple_metadata(self):
        """Test merging simple metadata."""
        trace = start_trace("test_operation")
        external_meta = {
            "confidence_score": 0.88,
            "routing_decision": "hybrid"
        }
        
        merge_trace_metadata(trace, external_meta)
        
        assert trace.metadata["confidence_score"] == 0.88
        assert trace.metadata["routing_decision"] == "hybrid"
    
    def test_merge_sums_latencies(self):
        """Test that latencies are summed when merging."""
        trace = start_trace("test_operation")
        trace.metadata["latency_ms_retrieval"] = 10.0
        
        external_meta = {
            "latency_ms_retrieval": 5.0,
            "latency_ms_llm": 100.0
        }
        
        merge_trace_metadata(trace, external_meta)
        
        assert trace.metadata["latency_ms_retrieval"] == 15.0
        assert trace.metadata["latency_ms_llm"] == 100.0
    
    def test_merge_takes_more_severe_degradation(self):
        """Test that more severe degradation level is kept."""
        trace = start_trace("test_operation")
        trace.metadata["degradation_level"] = "mild"
        
        external_meta = {
            "degradation_level": "degraded"
        }
        
        merge_trace_metadata(trace, external_meta)
        
        assert trace.metadata["degradation_level"] == "degraded"
    
    def test_merge_degradation_hierarchy(self):
        """Test degradation hierarchy during merge."""
        hierarchy = ["none", "mild", "fallback", "degraded", "failed"]
        
        # Test each combination
        trace = start_trace("test_operation")
        trace.metadata["degradation_level"] = "mild"
        
        merge_trace_metadata(trace, {"degradation_level": "failed"})
        assert trace.metadata["degradation_level"] == "failed"
        
        trace.metadata["degradation_level"] = "degraded"
        merge_trace_metadata(trace, {"degradation_level": "fallback"})
        assert trace.metadata["degradation_level"] == "degraded"


class TestTraceOperationContextManager:
    """Test the trace_operation context manager."""
    
    def test_context_manager_basic_usage(self):
        """Test basic context manager usage."""
        with trace_operation("test_op") as trace:
            assert trace.operation_name == "test_op"
            assert trace.start_time is not None
        
        # Should be finalized after context exit
        assert trace.end_time is not None
        assert trace.success is True
    
    def test_context_manager_handles_exceptions(self):
        """Test context manager handles exceptions."""
        try:
            with trace_operation("failing_op") as trace:
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Should mark as failed
        assert trace.success is False
        assert trace.metadata["error_class"] == "ValueError"
    
    def test_context_manager_allows_step_recording(self):
        """Test recording steps within context."""
        with trace_operation("test_op") as trace:
            record_step(trace, "step1", 10.0)
            record_step(trace, "step2", 20.0)
        
        assert "step1" in trace.steps
        assert "step2" in trace.steps
    
    def test_context_manager_allows_metadata_attachment(self):
        """Test attaching metadata within context."""
        with trace_operation("test_op") as trace:
            attach_metadata(
                trace,
                confidence_score=0.95,
                routing_decision="vector"
            )
        
        assert trace.metadata["confidence_score"] == 0.95
        assert trace.metadata["routing_decision"] == "vector"


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    def test_rag_pipeline_trace(self):
        """Test tracing a complete RAG pipeline."""
        with trace_operation("rag_ask") as trace:
            # Embedding step
            embeddings = safe_try(
                "embedding_generation",
                trace,
                lambda: [0.1, 0.2, 0.3],  # Mock embeddings
                fallback_value=None,
                fallback_message="Embedding service unavailable"
            )
            record_step(trace, "embedding", 15.0)
            
            # Retrieval step
            if embeddings:
                results = ["doc1", "doc2"]
                attach_metadata(trace, routing_decision="vector_search")
            else:
                results = ["doc1"]  # Keyword fallback
                attach_metadata(trace, routing_decision="keyword_fallback")
            
            record_step(trace, "retrieval", 25.0)
            
            # LLM step
            answer = "Machine learning is..."
            record_step(trace, "llm", 200.0)
            attach_metadata(trace, confidence_score=0.92)
        
        assert trace.success is True
        assert trace.metadata["latency_ms_embedding"] == 15.0
        assert trace.metadata["latency_ms_retrieval"] == 25.0
        assert trace.metadata["latency_ms_llm"] == 200.0
        assert trace.metadata["confidence_score"] == 0.92
    
    def test_degraded_pipeline_trace(self):
        """Test tracing a degraded pipeline."""
        with trace_operation("csv_insights") as trace:
            # LLM step fails
            def failing_llm():
                raise RuntimeError("LLM service unavailable")
            
            llm_insights = safe_try(
                "llm_narrative",
                trace,
                failing_llm,
                fallback_value=None,
                fallback_message="LLM unavailable, using statistical analysis only"
            )
            
            # Continue with deterministic analysis
            assert llm_insights is None
        
        assert trace.success is True  # Still succeeds
        assert trace.metadata["fallback_triggered"] is True
        assert trace.metadata["degradation_level"] == "fallback"
    
    def test_partial_failure_trace(self):
        """Test tracing partial failures."""
        with trace_operation("multi_doc_summary") as trace:
            successful = 8
            failed = 2
            
            attach_metadata(
                trace,
                degradation_level="mild" if failed > 0 else "none",
                graceful_message=f"{failed} documents failed processing"
            )
        
        assert trace.success is True
        assert trace.metadata["degradation_level"] == "mild"
        assert "failed processing" in trace.metadata["graceful_message"]
