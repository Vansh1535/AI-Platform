"""
Tests for CSV LLM Insights — Phase 2

Tests LLM-powered narrative insights with graceful degradation:
- Normal dataset → full LLM mode
- Weak dataset → degraded mode (deterministic fallback)
- LLM failure → deterministic fallback
- Tiny CSV → "insufficient data" mode
- Timeout scenarios → fallback handling
- Telemetry validation
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from app.analytics.csv_llm_insights import (
    generate_llm_narrative_insights,
    generate_deterministic_insights,
    should_enable_llm_insights,
    prepare_llm_context,
    MIN_ROWS_FOR_LLM,
    MIN_CONFIDENCE_FOR_LLM
)


class TestLLMInsightGeneration:
    """Test LLM insight generation with various scenarios."""
    
    def test_normal_dataset_full_llm_mode(self):
        """Test LLM insights with normal-sized dataset."""
        summary = {
            "rows": 100,
            "columns": 5,
            "numeric_columns": 3,
            "categorical_columns": 2
        }
        
        column_profiles = {
            "revenue": {
                "type": "numeric",
                "mean": 50000,
                "median": 48000,
                "std": 15000,
                "variance": 225000000,
                "null_count": 0
            },
            "category": {
                "type": "categorical",
                "unique_count": 10,
                "top_values": [("A", 30), ("B", 25)],
                "null_count": 0
            }
        }
        
        data_quality = {
            "null_ratio": 0.05,
            "duplicate_ratio": 0.01,
            "flags": []
        }
        
        # Mock LLM response
        mock_llm_response = {
            "text": """{
                "dataset_explanation": "This dataset contains 100 sales records with revenue metrics.",
                "key_patterns": ["Revenue shows normal distribution", "Category A is most common"],
                "relationships": ["Revenue correlates with category type"],
                "outliers_and_risks": ["No major outliers detected"],
                "data_quality_commentary": "Data is clean with minimal missing values."
            }""",
            "provider": "gemini",
            "raw": {}
        }
        
        with patch('app.analytics.csv_llm_insights.call_llm') as mock_call_llm:
            mock_call_llm.return_value = mock_llm_response
            
            result, telemetry = generate_llm_narrative_insights(
                summary, column_profiles, data_quality
            )
            
            # Validate LLM insights structure
            assert result['llm_insights']['enabled'] is True
            assert result['llm_insights']['mode'] == 'full'
            assert 'dataset_explanation' in result['llm_insights']
            assert 'key_patterns' in result['llm_insights']
            assert len(result['llm_insights']['key_patterns']) > 0
            
            # Validate telemetry
            assert telemetry['routing_decision'] == 'llm_full'
            assert telemetry['fallback_triggered'] is False
            assert telemetry['degradation_level'] == 'none'
            assert telemetry['latency_ms_llm'] >= 0  # Allow 0 for mocked calls
            assert telemetry['confidence_score'] == 0.9
    
    def test_tiny_dataset_deterministic_fallback(self):
        """Test fallback to deterministic mode for tiny datasets."""
        summary = {
            "rows": 5,  # Below MIN_ROWS_FOR_LLM (20)
            "columns": 3,
            "numeric_columns": 2,
            "categorical_columns": 1
        }
        
        column_profiles = {
            "value": {"type": "numeric", "mean": 100, "std": 10}
        }
        
        data_quality = {
            "null_ratio": 0.0,
            "duplicate_ratio": 0.0,
            "flags": []
        }
        
        result, telemetry = generate_llm_narrative_insights(
            summary, column_profiles, data_quality
        )
        
        # Should fallback to deterministic
        assert result['llm_insights']['enabled'] is False
        assert result['llm_insights']['mode'] == 'basic'
        assert 'insufficient_data' in telemetry['fallback_reason']
        assert telemetry['fallback_triggered'] is True
        assert telemetry['routing_decision'] == 'deterministic'
        assert telemetry['degradation_level'] == 'fallback'
        assert 'small' in telemetry['graceful_message'].lower()
    
    def test_low_quality_data_fallback(self):
        """Test fallback for low data quality."""
        summary = {
            "rows": 100,
            "columns": 5,
            "numeric_columns": 3,
            "categorical_columns": 2
        }
        
        column_profiles = {}
        
        data_quality = {
            "null_ratio": 0.8,  # 80% missing data
            "duplicate_ratio": 0.05,
            "flags": ["high_missing_values"]
        }
        
        result, telemetry = generate_llm_narrative_insights(
            summary, column_profiles, data_quality
        )
        
        # Should fallback due to quality
        assert result['llm_insights']['enabled'] is False
        assert result['llm_insights']['mode'] == 'basic'
        assert telemetry['fallback_reason'] == 'low_data_quality'
        assert telemetry['degradation_level'] == 'degraded'
        assert 'quality' in telemetry['graceful_message'].lower()
    
    def test_llm_timeout_fallback(self):
        """Test timeout handling with fallback."""
        summary = {
            "rows": 100,
            "columns": 5,
            "numeric_columns": 3,
            "categorical_columns": 2
        }
        
        column_profiles = {
            "col1": {"type": "numeric", "mean": 50, "std": 10}
        }
        
        data_quality = {
            "null_ratio": 0.05,
            "duplicate_ratio": 0.01,
            "flags": []
        }
        
        with patch('app.analytics.csv_llm_insights.call_llm') as mock_call_llm:
            mock_call_llm.side_effect = TimeoutError("LLM timeout")
            
            result, telemetry = generate_llm_narrative_insights(
                summary, column_profiles, data_quality, timeout=0.5
            )
            
            # Should gracefully fallback
            assert result['llm_insights']['enabled'] is False
            assert result['llm_insights']['mode'] == 'basic'
            assert telemetry['fallback_reason'] == 'llm_timeout'
            assert telemetry['fallback_triggered'] is True
            assert telemetry['degradation_level'] == 'fallback'
            assert 'timed out' in telemetry['graceful_message'].lower()
    
    def test_llm_parse_error_fallback(self):
        """Test fallback when LLM returns invalid JSON."""
        summary = {
            "rows": 100,
            "columns": 5,
            "numeric_columns": 3,
            "categorical_columns": 2
        }
        
        column_profiles = {
            "col1": {"type": "numeric", "mean": 50}
        }
        
        data_quality = {
            "null_ratio": 0.05,
            "duplicate_ratio": 0.01,
            "flags": []
        }
        
        # Mock LLM with invalid JSON
        mock_llm_response = {
            "text": "This is not JSON at all",
            "provider": "gemini",
            "raw": {}
        }
        
        with patch('app.analytics.csv_llm_insights.call_llm') as mock_call_llm:
            mock_call_llm.return_value = mock_llm_response
            
            result, telemetry = generate_llm_narrative_insights(
                summary, column_profiles, data_quality
            )
            
            # Should fallback due to parse error
            assert result['llm_insights']['enabled'] is False
            assert result['llm_insights']['mode'] == 'basic'
            assert 'llm_parse_error' in telemetry['fallback_reason']
            assert telemetry['fallback_triggered'] is True
            assert telemetry['degradation_level'] == 'fallback'
    
    def test_llm_missing_fields_fallback(self):
        """Test fallback when LLM response is missing required fields."""
        summary = {
            "rows": 100,
            "columns": 5,
            "numeric_columns": 3,
            "categorical_columns": 2
        }
        
        column_profiles = {
            "col1": {"type": "numeric", "mean": 50}
        }
        
        data_quality = {
            "null_ratio": 0.05,
            "duplicate_ratio": 0.01,
            "flags": []
        }
        
        # Mock LLM with incomplete response (missing fields)
        mock_llm_response = {
            "text": '{"dataset_explanation": "Some text", "key_patterns": []}',
            "provider": "gemini",
            "raw": {}
        }
        
        with patch('app.analytics.csv_llm_insights.call_llm') as mock_call_llm:
            mock_call_llm.return_value = mock_llm_response
            
            result, telemetry = generate_llm_narrative_insights(
                summary, column_profiles, data_quality
            )
            
            # Should fallback due to missing fields
            assert result['llm_insights']['enabled'] is False
            assert result['llm_insights']['mode'] == 'basic'
            assert telemetry['fallback_triggered'] is True


class TestDeterministicInsights:
    """Test deterministic insight generation (fallback mode)."""
    
    def test_basic_deterministic_insights(self):
        """Test basic deterministic insights generation."""
        summary = {
            "rows": 50,
            "columns": 4,
            "numeric_columns": 2,
            "categorical_columns": 2
        }
        
        column_profiles = {
            "revenue": {
                "type": "numeric",
                "variance": 5000,
                "mean": 1000
            },
            "category": {
                "type": "categorical",
                "unique_count": 15
            }
        }
        
        data_quality = {
            "null_ratio": 0.1,
            "duplicate_ratio": 0.05,
            "flags": []
        }
        
        result = generate_deterministic_insights(
            summary, column_profiles, data_quality
        )
        
        assert result['llm_insights']['enabled'] is False
        assert result['llm_insights']['mode'] == 'basic'
        assert '50 rows' in result['llm_insights']['dataset_explanation']
        assert '4 columns' in result['llm_insights']['dataset_explanation']
        assert len(result['llm_insights']['key_patterns']) > 0
        assert len(result['llm_insights']['relationships']) > 0
        assert len(result['llm_insights']['outliers_and_risks']) > 0
    
    def test_deterministic_high_variance_detection(self):
        """Test detection of high variance columns."""
        summary = {"rows": 100, "columns": 2, "numeric_columns": 1, "categorical_columns": 1}
        
        column_profiles = {
            "price": {
                "type": "numeric",
                "variance": 5000000,  # High variance
                "mean": 10000
            }
        }
        
        data_quality = {"null_ratio": 0.0, "duplicate_ratio": 0.0, "flags": []}
        
        result = generate_deterministic_insights(summary, column_profiles, data_quality)
        
        patterns = result['llm_insights']['key_patterns']
        assert any('variance' in p.lower() for p in patterns)
        assert any('price' in p for p in patterns)
    
    def test_deterministic_high_cardinality_detection(self):
        """Test detection of high cardinality categorical columns."""
        summary = {"rows": 100, "columns": 2, "numeric_columns": 0, "categorical_columns": 1}
        
        column_profiles = {
            "user_id": {
                "type": "categorical",
                "unique_count": 95  # 95% unique
            }
        }
        
        data_quality = {"null_ratio": 0.0, "duplicate_ratio": 0.0, "flags": []}
        
        result = generate_deterministic_insights(summary, column_profiles, data_quality)
        
        patterns = result['llm_insights']['key_patterns']
        assert any('cardinality' in p.lower() for p in patterns)
        assert any('user_id' in p for p in patterns)
    
    def test_deterministic_quality_issues_detection(self):
        """Test detection of data quality issues."""
        summary = {"rows": 100, "columns": 3, "numeric_columns": 2, "categorical_columns": 1}
        column_profiles = {}
        
        data_quality = {
            "null_ratio": 0.45,  # 45% missing
            "duplicate_ratio": 0.25,  # 25% duplicates
            "flags": ["high_missing_values", "high_duplicates"]
        }
        
        result = generate_deterministic_insights(summary, column_profiles, data_quality)
        
        risks = result['llm_insights']['outliers_and_risks']
        assert len(risks) == 2  # Both null and duplicate issues
        assert any('missing' in r.lower() or 'null' in r.lower() for r in risks)
        assert any('duplicate' in r.lower() for r in risks)
        
        commentary = result['llm_insights']['data_quality_commentary']
        assert 'flags' in commentary.lower() or 'cleaning' in commentary.lower()


class TestShouldEnableLLM:
    """Test decision logic for enabling LLM insights."""
    
    def test_enable_for_good_data(self):
        """Test LLM enabled for good quality data."""
        summary = {"rows": 50, "columns": 5}
        data_quality = {"null_ratio": 0.1, "flags": []}
        confidence = 0.8
        
        should_enable, reason = should_enable_llm_insights(summary, data_quality, confidence)
        
        assert should_enable is True
        assert reason == "enabled"
    
    def test_disable_for_tiny_dataset(self):
        """Test LLM disabled for tiny datasets."""
        summary = {"rows": 10, "columns": 3}  # Below MIN_ROWS_FOR_LLM
        data_quality = {"null_ratio": 0.0, "flags": []}
        confidence = 0.9
        
        should_enable, reason = should_enable_llm_insights(summary, data_quality, confidence)
        
        assert should_enable is False
        assert "insufficient_data" in reason
        assert "10_rows" in reason
    
    def test_disable_for_high_null_ratio(self):
        """Test LLM disabled for high missing data."""
        summary = {"rows": 100, "columns": 5}
        data_quality = {"null_ratio": 0.75, "flags": ["high_missing_values"]}  # 75% null
        confidence = 0.8
        
        should_enable, reason = should_enable_llm_insights(summary, data_quality, confidence)
        
        assert should_enable is False
        assert "high_null_ratio" in reason
    
    def test_disable_for_analysis_error(self):
        """Test LLM disabled when analysis has errors."""
        summary = {"rows": 100, "columns": 5}
        data_quality = {"null_ratio": 0.1, "flags": ["analysis_error"]}
        confidence = 0.8
        
        should_enable, reason = should_enable_llm_insights(summary, data_quality, confidence)
        
        assert should_enable is False
        assert "analysis_error" in reason
    
    def test_disable_for_low_confidence(self):
        """Test LLM disabled for low confidence scores."""
        summary = {"rows": 100, "columns": 5}
        data_quality = {"null_ratio": 0.1, "flags": []}
        confidence = 0.3  # Below MIN_CONFIDENCE_FOR_LLM (0.5)
        
        should_enable, reason = should_enable_llm_insights(summary, data_quality, confidence)
        
        assert should_enable is False
        assert "low_confidence" in reason


class TestLLMContextPreparation:
    """Test LLM context preparation from profiling data."""
    
    def test_context_includes_all_sections(self):
        """Test that context includes all required sections."""
        summary = {
            "rows": 100,
            "columns": 5,
            "numeric_columns": 3,
            "categorical_columns": 2
        }
        
        column_profiles = {
            "revenue": {
                "type": "numeric",
                "mean": 50000,
                "median": 48000,
                "std": 15000,
                "variance": 225000000,
                "null_count": 2,
                "min": 10000,
                "max": 100000
            },
            "category": {
                "type": "categorical",
                "unique_count": 10,
                "top_values": [("A", 30), ("B", 25), ("C", 20)],
                "null_count": 1
            }
        }
        
        data_quality = {
            "null_ratio": 0.02,
            "duplicate_ratio": 0.05,
            "flags": []
        }
        
        context = prepare_llm_context(summary, column_profiles, data_quality)
        
        # Parse JSON context
        import json
        context_dict = json.loads(context)
        
        # Validate structure
        assert "dataset_summary" in context_dict
        assert "numeric_columns" in context_dict
        assert "categorical_columns" in context_dict
        assert "data_quality" in context_dict
        
        # Validate content
        assert context_dict["dataset_summary"]["total_rows"] == 100
        assert "revenue" in context_dict["numeric_columns"]
        assert context_dict["numeric_columns"]["revenue"]["mean"] == 50000
        assert "category" in context_dict["categorical_columns"]
        assert context_dict["categorical_columns"]["category"]["unique_values"] == 10
    
    def test_context_excludes_raw_data(self):
        """Test that context never includes raw CSV rows (privacy)."""
        summary = {"rows": 50, "columns": 3}
        column_profiles = {
            "col1": {"type": "numeric", "mean": 100}
        }
        data_quality = {"null_ratio": 0.1, "flags": []}
        
        context = prepare_llm_context(summary, column_profiles, data_quality)
        
        # Context should only be aggregate statistics
        assert "row_" not in context.lower()
        assert "value" not in context.lower() or "top_values" in context.lower()  # top_values is OK
        import json
        context_dict = json.loads(context)
        
        # Ensure no list of individual data points
        for key, value in context_dict.items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    # Should not have lists of individual data points
                    if isinstance(subvalue, list) and subkey not in ["top_values"]:
                        assert len(subvalue) == 0 or not isinstance(subvalue[0], (int, float, str))


class TestTelemetryTracking:
    """Test telemetry tracking for LLM insights."""
    
    def test_telemetry_includes_latency(self):
        """Test that telemetry includes LLM latency."""
        summary = {"rows": 100, "columns": 5, "numeric_columns": 3, "categorical_columns": 2}
        column_profiles = {"col1": {"type": "numeric", "mean": 50}}
        data_quality = {"null_ratio": 0.05, "flags": []}
        
        mock_llm_response = {
            "text": """{
                "dataset_explanation": "Test",
                "key_patterns": ["Pattern 1"],
                "relationships": ["Relation 1"],
                "outliers_and_risks": ["Risk 1"],
                "data_quality_commentary": "Good"
            }""",
            "provider": "gemini",
            "raw": {}
        }
        
        with patch('app.analytics.csv_llm_insights.call_llm') as mock_call_llm:
            mock_call_llm.return_value = mock_llm_response
            
            result, telemetry = generate_llm_narrative_insights(
                summary, column_profiles, data_quality
            )
            
            assert 'latency_ms_llm' in telemetry
            assert isinstance(telemetry['latency_ms_llm'], int)
            assert telemetry['latency_ms_llm'] >= 0
    
    def test_telemetry_tracks_routing_decision(self):
        """Test that routing decision is tracked."""
        summary = {"rows": 5, "columns": 3}  # Too small
        column_profiles = {}
        data_quality = {"null_ratio": 0.0, "flags": []}
        
        result, telemetry = generate_llm_narrative_insights(
            summary, column_profiles, data_quality
        )
        
        assert 'routing_decision' in telemetry
        assert telemetry['routing_decision'] == 'deterministic'
    
    def test_telemetry_tracks_fallback_reason(self):
        """Test that fallback reasons are tracked."""
        summary = {"rows": 10, "columns": 3}  # Below threshold
        column_profiles = {}
        data_quality = {"null_ratio": 0.0, "flags": []}
        
        result, telemetry = generate_llm_narrative_insights(
            summary, column_profiles, data_quality
        )
        
        assert 'fallback_reason' in telemetry
        assert telemetry['fallback_reason'] is not None
        assert 'insufficient_data' in telemetry['fallback_reason']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
