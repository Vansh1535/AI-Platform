"""
Unit tests for CSV Insights Foundation (Phase C Step 2).

Tests analytical profiling capabilities including:
- Small dataset handling
- Missing values
- Duplicate detection
- Zero numeric columns case
- Data quality assessment
- Graceful messaging integration
"""

import pytest
import pandas as pd
import numpy as np
from app.analytics.csv_insights import (
    generate_csv_insights,
    infer_column_types,
    compute_numeric_profile,
    compute_categorical_profile,
    assess_data_quality,
    generate_narrative_insights,
    semantic_cluster_insights,
    trend_anomaly_scan,
    predictive_signal_preview
)


class TestColumnTypeInference:
    """Test column type inference logic."""
    
    def test_numeric_column_detection(self):
        """Numeric columns should be correctly identified."""
        df = pd.DataFrame({
            "age": [25, 30, 35, 40],
            "salary": [50000.0, 60000.0, 70000.0, 80000.0]
        })
        
        types = infer_column_types(df)
        
        assert types["age"] == "numeric"
        assert types["salary"] == "numeric"
    
    def test_categorical_numeric_detection(self):
        """Small cardinality numeric columns should be detected as categorical."""
        df = pd.DataFrame({
            "rating": [1, 2, 3, 1, 2, 3, 1, 2] * 10  # Low cardinality
        })
        
        types = infer_column_types(df)
        
        assert types["rating"] == "categorical_numeric"
    
    def test_categorical_text_detection(self):
        """Categorical text columns should be identified."""
        df = pd.DataFrame({
            "department": ["Sales", "Engineering", "HR", "Sales", "Engineering"] * 10
        })
        
        types = infer_column_types(df)
        
        assert types["department"] == "categorical"
    
    def test_high_cardinality_text(self):
        """High cardinality text should be marked as text, not categorical."""
        df = pd.DataFrame({
            "description": [f"Item description {i}" for i in range(100)]
        })
        
        types = infer_column_types(df)
        
        assert types["description"] == "text"


class TestNumericProfile:
    """Test numeric column profiling."""
    
    def test_basic_statistics(self):
        """Basic statistics should be computed correctly."""
        df = pd.DataFrame({
            "values": [10, 20, 30, 40, 50]
        })
        
        profile = compute_numeric_profile(df, "values")
        
        assert profile["count"] == 5
        assert profile["mean"] == 30.0
        assert profile["median"] == 30.0
        assert profile["min"] == 10.0
        assert profile["max"] == 50.0
        assert profile["null_count"] == 0
    
    def test_with_missing_values(self):
        """Profile should handle missing values correctly."""
        df = pd.DataFrame({
            "values": [10, 20, np.nan, 40, np.nan]
        })
        
        profile = compute_numeric_profile(df, "values")
        
        assert profile["count"] == 3
        assert profile["null_count"] == 2
        assert profile["mean"] == pytest.approx(23.33, rel=0.01)
    
    def test_skewness_detection(self):
        """Skewed distributions should be flagged."""
        # Right-skewed data
        df = pd.DataFrame({
            "values": [1, 2, 3, 4, 5, 100, 200, 300]
        })
        
        profile = compute_numeric_profile(df, "values")
        
        assert "skew_note" in profile
        assert "skewed" in profile["skew_note"]
    
    def test_all_null_column(self):
        """All-null columns should return zero counts."""
        df = pd.DataFrame({
            "values": [np.nan, np.nan, np.nan]
        })
        
        profile = compute_numeric_profile(df, "values")
        
        assert profile["count"] == 0
        assert profile["null_count"] == 3
        assert profile["mean"] is None


class TestCategoricalProfile:
    """Test categorical column profiling."""
    
    def test_category_distribution(self):
        """Category counts and percentages should be computed."""
        df = pd.DataFrame({
            "department": ["Sales", "Engineering", "Sales", "HR", "Engineering"]
        })
        
        profile = compute_categorical_profile(df, "department")
        
        assert profile["count"] == 5
        assert profile["unique_values"] == 3
        assert "Sales" in profile["top_categories"]
        assert profile["top_categories"]["Sales"]["count"] == 2
    
    def test_dominance_detection(self):
        """Dominated categories should be flagged."""
        df = pd.DataFrame({
            "status": ["Active"] * 90 + ["Inactive"] * 10
        })
        
        profile = compute_categorical_profile(df, "status")
        
        assert "dominance_note" in profile
        assert "Active" in profile["dominance_note"]
    
    def test_category_limit(self):
        """Should limit number of top categories shown."""
        categories = [f"Cat{i}" for i in range(50)]
        df = pd.DataFrame({
            "category": np.random.choice(categories, 1000)
        })
        
        profile = compute_categorical_profile(df, "category")
        
        # Should not exceed MAX_CATEGORIES_TO_SHOW (10)
        assert len(profile["top_categories"]) <= 10


class TestDataQuality:
    """Test data quality assessment."""
    
    def test_basic_quality_metrics(self):
        """Basic quality metrics should be computed."""
        df = pd.DataFrame({
            "a": [1, 2, 3],
            "b": [4, 5, 6]
        })
        
        quality = assess_data_quality(df)
        
        assert quality["total_rows"] == 3
        assert quality["total_columns"] == 2
        assert quality["total_cells"] == 6
        assert quality["null_cells"] == 0
        assert quality["duplicate_rows"] == 0
    
    def test_high_null_ratio_flag(self):
        """High missing values should be flagged."""
        df = pd.DataFrame({
            "a": [1, np.nan, np.nan, np.nan, np.nan],
            "b": [np.nan, np.nan, 3, np.nan, np.nan]
        })
        
        quality = assess_data_quality(df)
        
        assert "high_missing_values" in quality["flags"]
        assert quality["null_ratio"] > 0.5
    
    def test_duplicate_detection(self):
        """Duplicates should be detected and counted."""
        df = pd.DataFrame({
            "a": [1, 2, 1, 2, 3],
            "b": [4, 5, 4, 5, 6]
        })
        
        quality = assess_data_quality(df)
        
        assert quality["duplicate_rows"] == 2
        assert quality["duplicate_ratio"] == 0.4
    
    def test_small_dataset_flag(self):
        """Small datasets should be flagged."""
        df = pd.DataFrame({
            "a": [1, 2, 3]
        })
        
        quality = assess_data_quality(df)
        
        assert "small_dataset" in quality["flags"]
    
    def test_wide_table_flag(self):
        """Wide tables should be flagged."""
        data = {f"col{i}": [1, 2, 3] for i in range(60)}
        df = pd.DataFrame(data)
        
        quality = assess_data_quality(df)
        
        assert "wide_table" in quality["flags"]


class TestNarrativeInsights:
    """Test narrative insight generation."""
    
    def test_basic_narrative(self):
        """Should generate basic dataset description."""
        column_profiles = {
            "age": {"type": "numeric"},
            "department": {"type": "categorical"}
        }
        column_types = {"age": "numeric", "department": "categorical"}
        data_quality = {"total_rows": 100, "total_columns": 2, "flags": []}
        
        narrative = generate_narrative_insights(
            column_profiles,
            column_types,
            data_quality
        )
        
        assert "100" in narrative
        assert "2 columns" in narrative or "columns" in narrative
    
    def test_skew_mention(self):
        """Skewed columns should be mentioned."""
        column_profiles = {
            "salary": {"type": "numeric", "skew_note": "right-skewed"}
        }
        column_types = {"salary": "numeric"}
        data_quality = {"total_rows": 100, "total_columns": 1, "flags": []}
        
        narrative = generate_narrative_insights(
            column_profiles,
            column_types,
            data_quality
        )
        
        assert "skewed" in narrative.lower()


class TestGenerateCSVInsights:
    """Test main insights generation function."""
    
    def test_small_dataset_fallback(self):
        """Should gracefully handle small datasets."""
        df = pd.DataFrame({
            "a": [1, 2, 3],
            "b": [4, 5, 6]
        })
        
        insights, telemetry = generate_csv_insights(df)
        
        assert insights["summary"]["analysis_performed"] is False
        assert "small_dataset" in insights["data_quality"]["flags"]
        assert telemetry["degradation_level"] == "fallback"
        assert telemetry["graceful_message"] is not None
    
    def test_zero_numeric_columns(self):
        """Should handle datasets with no numeric columns."""
        df = pd.DataFrame({
            "name": ["Alice", "Bob", "Charlie"] * 10,
            "department": ["Sales", "Engineering", "HR"] * 10
        })
        
        insights, telemetry = generate_csv_insights(df)
        
        assert insights["summary"]["numeric_columns"] == 0
        assert telemetry["degradation_level"] == "fallback"
        assert "text columns" in insights["insight_notes"]
    
    def test_successful_analysis(self):
        """Should successfully analyze a normal dataset."""
        df = pd.DataFrame({
            "age": np.random.randint(20, 60, 100),
            "salary": np.random.randint(40000, 120000, 100),
            "department": np.random.choice(["Sales", "Engineering", "HR"], 100)
        })
        
        insights, telemetry = generate_csv_insights(df)
        
        assert insights["summary"]["analysis_performed"] is True
        assert insights["summary"]["numeric_columns"] >= 2
        assert len(insights["column_profiles"]) == 3
        assert telemetry["degradation_level"] == "none"
        assert telemetry["graceful_message"] is None
    
    def test_high_missing_values(self):
        """Should flag high missing value ratio."""
        df = pd.DataFrame({
            "a": [1] * 10 + [np.nan] * 40,
            "b": [2] * 10 + [np.nan] * 40,
            "c": [3] * 10 + [np.nan] * 40
        })
        
        insights, telemetry = generate_csv_insights(df)
        
        assert "high_missing_values" in insights["data_quality"]["flags"]
        # Should have mild degradation but still have results
        assert telemetry["degradation_level"] in ["mild", "fallback"]
    
    def test_with_duplicates(self):
        """Should detect and report duplicates."""
        df = pd.DataFrame({
            "a": [1, 2, 3, 1, 2] * 10,
            "b": [4, 5, 6, 4, 5] * 10
        })
        
        insights, telemetry = generate_csv_insights(df)
        
        assert insights["data_quality"]["duplicate_rows"] > 0
        assert insights["data_quality"]["duplicate_ratio"] > 0
    
    def test_mixed_types(self):
        """Should handle mixed column types correctly."""
        df = pd.DataFrame({
            "id": range(50),
            "name": [f"Person{i}" for i in range(50)],
            "age": np.random.randint(20, 60, 50),
            "department": np.random.choice(["A", "B", "C"], 50),
            "salary": np.random.random(50) * 100000,
            "active": np.random.choice([True, False], 50)
        })
        
        insights, telemetry = generate_csv_insights(df)
        
        assert insights["summary"]["analysis_performed"] is True
        assert len(insights["column_profiles"]) == 6
        
        # Check various type handling
        profiles = insights["column_profiles"]
        assert any(p["type"] == "numeric" for p in profiles.values())
        assert any(p["type"] == "categorical" for p in profiles.values())
    
    def test_column_profiling_error_handling(self):
        """Should handle errors in individual column profiling gracefully."""
        # Create a dataframe that might cause profiling issues
        df = pd.DataFrame({
            "normal": range(20),
            "mixed": [1, "text", 3, None, 5] * 4  # Mixed types
        })
        
        # Should not crash, even with problematic columns
        insights, telemetry = generate_csv_insights(df)
        
        assert insights["summary"]["analysis_performed"] is True


class TestFuturePlaceholders:
    """Test future-ready placeholder functions."""
    
    def test_semantic_cluster_placeholder(self):
        """Semantic clustering should return not-enabled message."""
        result = semantic_cluster_insights([])
        
        assert result["status"] == "not_enabled"
        assert "not enabled yet" in result["message"]
        assert "phase_c_step_3" in result["available_in"]
    
    def test_trend_anomaly_placeholder(self):
        """Trend anomaly scan should return not-enabled message."""
        df = pd.DataFrame({"values": [1, 2, 3]})
        result = trend_anomaly_scan(df)
        
        assert result["status"] == "not_enabled"
        assert "not enabled yet" in result["message"]
    
    def test_predictive_signal_placeholder(self):
        """Predictive signal preview should return not-enabled message."""
        df = pd.DataFrame({"values": [1, 2, 3]})
        result = predictive_signal_preview(df)
        
        assert result["status"] == "not_enabled"
        assert "not enabled yet" in result["message"]


class TestGracefulMessaging:
    """Test graceful messaging integration."""
    
    def test_small_dataset_message(self):
        """Small dataset should have appropriate graceful message."""
        df = pd.DataFrame({"a": [1, 2]})
        
        insights, telemetry = generate_csv_insights(df)
        
        assert telemetry["graceful_message"] is not None
        assert "enough" in telemetry["graceful_message"].lower()
        assert telemetry["user_action_hint"] is not None
    
    def test_no_numeric_columns_message(self):
        """Zero numeric columns should have appropriate message."""
        df = pd.DataFrame({
            "text1": ["a", "b", "c"] * 10,
            "text2": ["d", "e", "f"] * 10
        })
        
        insights, telemetry = generate_csv_insights(df)
        
        assert telemetry["graceful_message"] is not None
        assert telemetry["degradation_level"] == "fallback"
    
    def test_success_no_message(self):
        """Successful analysis should have no graceful message."""
        df = pd.DataFrame({
            "a": range(50),
            "b": range(50, 100)
        })
        
        insights, telemetry = generate_csv_insights(df)
        
        if telemetry["degradation_level"] == "none":
            assert telemetry["graceful_message"] is None
    
    def test_metadata_preserved(self):
        """Technical metadata should always be preserved."""
        df = pd.DataFrame({"a": range(50)})
        file_meta = {"source": "test.csv", "custom_field": "value"}
        
        insights, telemetry = generate_csv_insights(df, file_meta)
        
        assert telemetry["source"] == "test.csv"
        assert telemetry["routing"] == "csv_insights"
        assert telemetry["rows"] == 50
        assert telemetry["columns"] == 1


if __name__ == "__main__":
    print("Running CSV insights tests...")
    pytest.main([__file__, "-v"])
