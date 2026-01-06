"""
Unit Tests for CSV Profiler Module

Tests comprehensive CSV profiling with:
- Normal datasets
- Edge cases (tiny, empty, corrupted)
- Data quality scenarios
- Graceful fallback behavior
- Type detection accuracy
"""

import pytest
import pandas as pd
import numpy as np
from app.insights.csv_profiler import (
    profile_csv_data,
    detect_column_type,
    profile_numeric_column,
    profile_categorical_column,
    assess_data_quality,
    generate_narrative_insights
)


class TestColumnTypeDetection:
    """Test column type detection logic."""
    
    def test_numeric_column(self):
        """Pure numeric columns detected correctly."""
        series = pd.Series([1, 2, 3, 4, 5])
        col_type = detect_column_type(series, "test_col")
        assert col_type == "numeric"
    
    def test_low_cardinality_numeric_as_categorical(self):
        """Low cardinality numeric columns detected as categorical."""
        series = pd.Series([1, 2, 1, 2, 1, 2] * 10)
        col_type = detect_column_type(series, "test_col")
        assert col_type == "categorical"
    
    def test_categorical_column(self):
        """Categorical columns detected correctly."""
        series = pd.Series(["A", "B", "C", "A", "B", "C"])
        col_type = detect_column_type(series, "test_col")
        assert col_type == "categorical"
    
    def test_text_column(self):
        """High cardinality text columns detected."""
        series = pd.Series([f"Text item {i}" for i in range(200)])
        col_type = detect_column_type(series, "test_col")
        assert col_type == "text"
    
    def test_empty_column(self):
        """Empty columns return unknown type."""
        series = pd.Series([np.nan] * 10)
        col_type = detect_column_type(series, "test_col")
        assert col_type == "unknown"


class TestDataQualityAssessment:
    """Test data quality assessment logic."""
    
    def test_good_quality(self):
        """Good quality data identified correctly."""
        quality = assess_data_quality(0.1, 0.5, "numeric")
        assert quality == "good"
    
    def test_weak_quality_high_missing(self):
        """High missing ratio flagged as weak."""
        quality = assess_data_quality(0.6, 0.5, "numeric")
        assert quality == "weak"
    
    def test_poor_quality_very_high_missing(self):
        """Very high missing ratio flagged as poor."""
        quality = assess_data_quality(0.85, 0.5, "numeric")
        assert quality == "poor"
    
    def test_weak_quality_low_diversity(self):
        """Low diversity categorical flagged as weak."""
        quality = assess_data_quality(0.1, 0.005, "categorical")
        assert quality == "weak"


class TestNumericProfiling:
    """Test numeric column profiling."""
    
    def test_basic_statistics(self):
        """Basic statistics computed correctly."""
        series = pd.Series([10, 20, 30, 40, 50])
        profile = profile_numeric_column(series, "test_col")
        
        assert profile["sufficient_data"] is True
        assert profile["min"] == 10
        assert profile["max"] == 50
        assert profile["mean"] == 30
        assert profile["median"] == 30
        assert profile["value_range"] == 40
    
    def test_zero_and_negative_counts(self):
        """Zero and negative counts tracked."""
        series = pd.Series([-5, -2, 0, 0, 0, 5, 10])
        profile = profile_numeric_column(series, "test_col")
        
        assert profile["zero_count"] == 3
        assert profile["negative_count"] == 2
        assert profile["has_negatives"] is True
    
    def test_outlier_detection(self):
        """Outliers detected using z-score."""
        # Need more data points for robust outlier detection
        series = pd.Series([10, 11, 12, 11, 10, 11, 10, 11, 12, 11, 1000])
        profile = profile_numeric_column(series, "test_col")
        
        assert profile["outlier_indicator"] == "outliers_detected"
    
    def test_stability_assessment(self):
        """Stability flag computed correctly."""
        # Stable data
        stable_series = pd.Series([100, 101, 99, 100, 101])
        stable_profile = profile_numeric_column(stable_series, "stable")
        assert stable_profile["stability_flag"] == "stable"
        
        # Variable data
        variable_series = pd.Series([10, 50, 100, 20, 80])
        variable_profile = profile_numeric_column(variable_series, "variable")
        assert variable_profile["stability_flag"] in ["variable", "highly_variable"]
    
    def test_insufficient_data(self):
        """Handles insufficient data gracefully."""
        series = pd.Series([5])
        profile = profile_numeric_column(series, "test_col")
        
        assert profile["sufficient_data"] is False


class TestCategoricalProfiling:
    """Test categorical column profiling."""
    
    def test_top_values_frequency(self):
        """Top values with frequencies computed."""
        series = pd.Series(["A"] * 50 + ["B"] * 30 + ["C"] * 20)
        profile = profile_categorical_column(series, "test_col")
        
        assert profile["unique_count"] == 3
        assert len(profile["top_values"]) == 3
        assert profile["top_values"][0]["value"] == "A"
        assert profile["top_values"][0]["count"] == 50
        assert profile["top_values"][0]["frequency"] == 0.5
    
    def test_dominance_detection(self):
        """Single value dominance detected."""
        series = pd.Series(["A"] * 90 + ["B"] * 10)
        profile = profile_categorical_column(series, "test_col")
        
        assert profile["dominance_detected"] is True
        assert profile["dominant_value"] == "A"
    
    def test_diversity_indicators(self):
        """Diversity indicators computed correctly."""
        # Low diversity
        low_div = pd.Series(["A", "B", "A", "B"])
        low_profile = profile_categorical_column(low_div, "low")
        assert "low" in low_profile["diversity_indicator"]
        
        # High diversity
        high_div = pd.Series([f"Cat{i}" for i in range(50)])
        high_profile = profile_categorical_column(high_div, "high")
        assert "high" in high_profile["diversity_indicator"]
    
    def test_health_flags(self):
        """Health flags assigned correctly."""
        # Good health
        good_series = pd.Series(["A"] * 25 + ["B"] * 25 + ["C"] * 25 + ["D"] * 25)
        good_profile = profile_categorical_column(good_series, "good")
        assert good_profile["health_flag"] == "good"
        
        # Poor health (extreme dominance)
        poor_series = pd.Series(["A"] * 98 + ["B"] * 2)
        poor_profile = profile_categorical_column(poor_series, "poor")
        assert poor_profile["health_flag"] == "poor"
    
    def test_empty_column(self):
        """Empty categorical column handled."""
        series = pd.Series([np.nan] * 10)
        profile = profile_categorical_column(series, "empty")
        
        assert profile["unique_count"] == 0
        assert profile["diversity_indicator"] == "no_data"
        assert profile["health_flag"] == "poor"


class TestNarrativeInsights:
    """Test narrative insight generation."""
    
    def test_basic_narrative(self):
        """Basic narrative generated correctly."""
        profiles = [
            {"type": "numeric", "quality_flag": "good", "column_name": "col1", "missing_ratio": 0.1},
            {"type": "categorical", "quality_flag": "good", "column_name": "col2", "missing_ratio": 0.05}
        ]
        
        insights = generate_narrative_insights(profiles, 100, 2)
        
        assert "100 rows" in insights["summary_text"]
        assert "2 columns" in insights["summary_text"]
        assert insights["confidence_level"] in ["high", "medium", "low"]
        assert isinstance(insights["warnings"], list)
    
    def test_warnings_for_poor_quality(self):
        """Warnings generated for poor quality data."""
        profiles = [
            {"type": "numeric", "quality_flag": "poor", "column_name": "col1", "missing_ratio": 0.9}
        ]
        
        insights = generate_narrative_insights(profiles, 50, 1)
        
        assert len(insights["warnings"]) > 0
        assert any("missing" in w.lower() or "quality" in w.lower() for w in insights["warnings"])
    
    def test_low_confidence_for_small_dataset(self):
        """Low confidence for very small datasets."""
        profiles = [
            {"type": "numeric", "quality_flag": "good", "column_name": "col1", "missing_ratio": 0.0}
        ]
        
        insights = generate_narrative_insights(profiles, 2, 1)
        
        assert insights["confidence_level"] == "low"


class TestFullProfiling:
    """Test end-to-end profiling scenarios."""
    
    def test_normal_dataset(self):
        """Normal dataset profiles successfully."""
        df = pd.DataFrame({
            "age": [25, 30, 35, 40, 45],
            "department": ["Sales", "Engineering", "Sales", "HR", "Engineering"],
            "salary": [50000, 60000, 55000, 58000, 62000]
        })
        
        result, telemetry = profile_csv_data(df, "test_normal")
        
        assert result["profile"]["row_count"] == 5
        assert result["profile"]["column_count"] == 3
        assert len(result["profile"]["columns"]) == 3
        assert result["insights"]["confidence_level"] in ["high", "medium"]
        assert telemetry["processing_mode"] in ["full", "partial"]
        assert telemetry["latency_ms"] > 0
    
    def test_empty_dataframe(self):
        """Empty DataFrame handled gracefully."""
        df = pd.DataFrame()
        
        result, telemetry = profile_csv_data(df, "test_empty")
        
        assert result["profile"]["row_count"] == 0
        assert result["profile"]["column_count"] == 0
        assert telemetry["processing_mode"] == "fallback"
        assert telemetry["degradation_level"] == "failed"
        assert telemetry["graceful_message"] is not None
        assert telemetry["fallback_reason"] == "empty_dataframe"
    
    def test_single_row_dataset(self):
        """Single row dataset triggers fallback."""
        df = pd.DataFrame({
            "col1": [1],
            "col2": ["A"]
        })
        
        result, telemetry = profile_csv_data(df, "test_single_row")
        
        assert result["profile"]["row_count"] == 1
        assert telemetry["processing_mode"] == "fallback"
        assert telemetry["degradation_level"] == "fallback"
        assert "too few rows" in telemetry["graceful_message"].lower()
    
    def test_tiny_dataset(self):
        """Tiny dataset (2 rows) profiles with warnings."""
        df = pd.DataFrame({
            "col1": [1, 2],
            "col2": ["A", "B"]
        })
        
        result, telemetry = profile_csv_data(df, "test_tiny")
        
        assert result["profile"]["row_count"] == 2
        assert telemetry["processing_mode"] in ["partial", "full"]
        assert telemetry["degradation_level"] in ["mild", "none"]
    
    def test_high_missing_values(self):
        """Dataset with many missing values handled."""
        df = pd.DataFrame({
            "col1": [1, np.nan, np.nan, np.nan, 5],
            "col2": ["A", np.nan, np.nan, "B", np.nan]
        })
        
        result, telemetry = profile_csv_data(df, "test_missing")
        
        # Should still profile successfully
        assert len(result["profile"]["columns"]) == 2
        
        # Check for high missing ratio
        col1_profile = result["profile"]["columns"][0]
        assert col1_profile["missing_ratio"] > 0.5
        
        # Warnings should be present
        assert len(result["insights"]["warnings"]) > 0
    
    def test_mixed_type_column(self):
        """Mixed type columns handled gracefully."""
        df = pd.DataFrame({
            "mixed": [1, "text", 3, "more text", 5]
        })
        
        result, telemetry = profile_csv_data(df, "test_mixed")
        
        # Should complete without crashing
        assert len(result["profile"]["columns"]) == 1
        assert result["profile"]["columns"][0]["type"] in ["numeric", "categorical", "text", "mixed"]
    
    def test_all_text_dataset(self):
        """All-text dataset profiles correctly."""
        df = pd.DataFrame({
            "text1": ["Sample text A", "Sample text B", "Sample text C"],
            "text2": ["More text X", "More text Y", "More text Z"]
        })
        
        result, telemetry = profile_csv_data(df, "test_all_text")
        
        assert len(result["profile"]["columns"]) == 2
        # Should detect as text or categorical
        types = [col["type"] for col in result["profile"]["columns"]]
        assert all(t in ["text", "categorical"] for t in types)
    
    def test_high_cardinality_category(self):
        """High cardinality categorical column handled."""
        df = pd.DataFrame({
            "category": [f"Cat{i}" for i in range(150)]
        })
        
        result, telemetry = profile_csv_data(df, "test_high_card")
        
        assert len(result["profile"]["columns"]) == 1
        col_profile = result["profile"]["columns"][0]
        assert col_profile["type"] in ["text", "categorical"]
        
        # Should have unique count
        assert col_profile["unique_count"] == 150
    
    def test_corrupted_values_partial_failure(self):
        """Corrupted values in some columns handled."""
        # Create DataFrame with problematic column
        df = pd.DataFrame({
            "good_col": [1, 2, 3, 4, 5],
            "problem_col": [None, None, None, None, None]
        })
        
        result, telemetry = profile_csv_data(df, "test_corrupted")
        
        # Should still profile the good column
        assert len(result["profile"]["columns"]) >= 1
    
    def test_numeric_with_outliers(self):
        """Numeric columns with outliers detected."""
        df = pd.DataFrame({
            # Need more data points for robust outlier detection
            "values": [10, 11, 12, 11, 10, 11, 10, 11, 12, 11, 1000]
        })
        
        result, telemetry = profile_csv_data(df, "test_outliers")
        
        col_profile = result["profile"]["columns"][0]
        if "numeric_stats" in col_profile:
            assert col_profile["numeric_stats"]["outlier_indicator"] == "outliers_detected"
        else:
            # Ensure it was profiled as numeric
            assert col_profile["type"] == "numeric"
    
    def test_categorical_with_dominance(self):
        """Categorical columns with dominance detected."""
        df = pd.DataFrame({
            "status": ["Active"] * 95 + ["Inactive"] * 5
        })
        
        result, telemetry = profile_csv_data(df, "test_dominance")
        
        col_profile = result["profile"]["columns"][0]
        if "categorical_stats" in col_profile:
            assert col_profile["categorical_stats"]["dominance_detected"] is True
            assert col_profile["categorical_stats"]["dominant_value"] == "Active"


class TestGracefulBehavior:
    """Test graceful fallback and error handling."""
    
    def test_no_crash_on_empty(self):
        """No crash on empty DataFrame."""
        df = pd.DataFrame()
        result, telemetry = profile_csv_data(df)
        
        assert result is not None
        assert telemetry is not None
        assert telemetry["graceful_message"] is not None
    
    def test_no_crash_on_all_nulls(self):
        """No crash when all values are null."""
        df = pd.DataFrame({
            "col1": [np.nan] * 10,
            "col2": [np.nan] * 10
        })
        
        result, telemetry = profile_csv_data(df, "test_all_nulls")
        
        assert result is not None
        assert len(result["profile"]["columns"]) == 2
    
    def test_graceful_message_present_on_fallback(self):
        """Graceful message present when fallback triggered."""
        df = pd.DataFrame({"col": [1]})  # Single row
        
        result, telemetry = profile_csv_data(df)
        
        assert telemetry["graceful_message"] is not None
        assert telemetry["fallback_reason"] is not None
        assert telemetry["user_action_hint"] is not None
    
    def test_telemetry_fields_always_present(self):
        """All required telemetry fields always present."""
        df = pd.DataFrame({"col": [1, 2, 3]})
        
        result, telemetry = profile_csv_data(df)
        
        required_fields = [
            "routing", "source", "latency_ms", "processing_mode",
            "degradation_level", "graceful_message", "fallback_reason", "user_action_hint"
        ]
        
        for field in required_fields:
            assert field in telemetry, f"Missing required field: {field}"


class TestDeterminism:
    """Test that profiling is deterministic."""
    
    def test_consistent_results(self):
        """Same dataset produces consistent results."""
        df = pd.DataFrame({
            "age": [25, 30, 35, 40, 45],
            "department": ["Sales", "Eng", "Sales", "HR", "Eng"]
        })
        
        result1, _ = profile_csv_data(df, "test1")
        result2, _ = profile_csv_data(df, "test2")
        
        # Row/column counts should match
        assert result1["profile"]["row_count"] == result2["profile"]["row_count"]
        assert result1["profile"]["column_count"] == result2["profile"]["column_count"]
        
        # Column types should match
        types1 = [col["type"] for col in result1["profile"]["columns"]]
        types2 = [col["type"] for col in result2["profile"]["columns"]]
        assert types1 == types2
        
        # Insights should be identical
        assert result1["insights"]["summary_text"] == result2["insights"]["summary_text"]
        assert result1["insights"]["confidence_level"] == result2["insights"]["confidence_level"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
