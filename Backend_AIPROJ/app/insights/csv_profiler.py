"""
CSV Profiler - Structured Analytical Profiling Foundation

Provides comprehensive CSV profiling with:
- Column-level type detection and quality assessment
- Descriptive statistics for numeric columns
- Categorical distribution analysis
- Lightweight narrative insights (rule-based, no LLM)
- Graceful fallback behavior for edge cases
- Production-grade observability

Design Principles:
- Never crash - always return structured output
- Graceful degradation for poor quality data
- Deterministic insights (no LLM hallucinations)
- Consistent with platform graceful messaging conventions
"""

import time
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from collections import Counter
import logging

logger = logging.getLogger(__name__)

# Thresholds and constants
MIN_ROWS_FOR_FULL_PROFILE = 3
MIN_ROWS_FOR_STATS = 2
HIGH_MISSING_RATIO = 0.5
HIGH_CARDINALITY_THRESHOLD = 100
LOW_CARDINALITY_THRESHOLD = 10
DOMINANCE_THRESHOLD = 0.8
MAX_SAMPLE_VALUES = 5
MAX_TOP_CATEGORIES = 10
OUTLIER_Z_THRESHOLD = 3.0
HIGH_VARIANCE_CV_THRESHOLD = 0.5  # Coefficient of variation


def detect_column_type(series: pd.Series, column_name: str) -> str:
    """
    Detect the semantic type of a column.
    
    Types: numeric | categorical | text | mixed | unknown
    
    Args:
        series: Pandas Series to analyze
        column_name: Name of the column (for logging)
        
    Returns:
        Column type string
    """
    # Remove nulls for type detection
    non_null = series.dropna()
    
    if len(non_null) == 0:
        return "unknown"
    
    # Check if numeric
    if pd.api.types.is_numeric_dtype(series):
        unique_count = non_null.nunique()
        total_count = len(non_null)
        
        # Low cardinality numeric might be categorical
        if unique_count <= LOW_CARDINALITY_THRESHOLD and total_count >= 20:
            return "categorical"
        return "numeric"
    
    # Check if all values can be converted to numeric
    try:
        pd.to_numeric(non_null, errors='raise')
        return "numeric"
    except (ValueError, TypeError):
        pass
    
    # Check cardinality for categorical vs text
    unique_count = non_null.nunique()
    total_count = len(non_null)
    
    if unique_count <= LOW_CARDINALITY_THRESHOLD:
        return "categorical"
    elif unique_count > HIGH_CARDINALITY_THRESHOLD:
        return "text"
    else:
        # Medium cardinality - check average text length
        avg_length = non_null.astype(str).str.len().mean()
        if avg_length > 50:
            return "text"
        else:
            return "categorical"


def assess_data_quality(missing_ratio: float, unique_ratio: float, column_type: str) -> str:
    """
    Assess data quality for a column.
    
    Args:
        missing_ratio: Ratio of missing values (0-1)
        unique_ratio: Ratio of unique values to total (0-1)
        column_type: Detected column type
        
    Returns:
        Quality flag: "good" | "weak" | "poor"
    """
    if missing_ratio >= 0.8:
        return "poor"
    elif missing_ratio >= HIGH_MISSING_RATIO:
        return "weak"
    
    # For categorical columns, check if too many nulls or too few unique values
    if column_type == "categorical":
        if unique_ratio < 0.01 and missing_ratio < 0.3:
            return "weak"  # Very low diversity
    
    return "good"


def profile_numeric_column(series: pd.Series, column_name: str) -> Dict[str, Any]:
    """
    Generate comprehensive profile for numeric column.
    
    Returns:
        - min, max, mean, median, stddev
        - value range
        - zero count, negative presence
        - outlier indicator
        - stability flag
    """
    non_null = series.dropna()
    
    if len(non_null) < MIN_ROWS_FOR_STATS:
        return {
            "type": "numeric",
            "sufficient_data": False,
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "stddev": None,
            "value_range": None,
            "zero_count": 0,
            "negative_count": 0,
            "outlier_indicator": "insufficient_data",
            "stability_flag": "unknown"
        }
    
    try:
        # Convert to numeric if not already
        numeric_values = pd.to_numeric(non_null, errors='coerce').dropna()
        
        if len(numeric_values) == 0:
            return {
                "type": "numeric",
                "sufficient_data": False,
                "conversion_failed": True
            }
        
        min_val = float(numeric_values.min())
        max_val = float(numeric_values.max())
        mean_val = float(numeric_values.mean())
        median_val = float(numeric_values.median())
        std_val = float(numeric_values.std())
        
        # Counts
        zero_count = int((numeric_values == 0).sum())
        negative_count = int((numeric_values < 0).sum())
        
        # Outlier detection using z-score
        if std_val > 0:
            z_scores = np.abs((numeric_values - mean_val) / std_val)
            outlier_count = int((z_scores > OUTLIER_Z_THRESHOLD).sum())
            outlier_indicator = "outliers_detected" if outlier_count > 0 else "no_outliers"
        else:
            outlier_indicator = "zero_variance"
        
        # Stability assessment using coefficient of variation
        if mean_val != 0:
            cv = abs(std_val / mean_val)
            if cv > HIGH_VARIANCE_CV_THRESHOLD:
                stability_flag = "highly_variable"
            elif cv > 0.2:
                stability_flag = "variable"
            else:
                stability_flag = "stable"
        else:
            stability_flag = "zero_mean"
        
        return {
            "type": "numeric",
            "sufficient_data": True,
            "min": min_val,
            "max": max_val,
            "mean": mean_val,
            "median": median_val,
            "stddev": std_val,
            "value_range": max_val - min_val,
            "zero_count": zero_count,
            "negative_count": negative_count,
            "has_negatives": negative_count > 0,
            "outlier_indicator": outlier_indicator,
            "stability_flag": stability_flag
        }
        
    except Exception as e:
        logger.warning(f"Failed to profile numeric column {column_name}: {str(e)}")
        return {
            "type": "numeric",
            "sufficient_data": False,
            "error": str(e)
        }


def profile_categorical_column(series: pd.Series, column_name: str) -> Dict[str, Any]:
    """
    Generate comprehensive profile for categorical column.
    
    Returns:
        - top-k values with frequency
        - entropy/diversity indicator
        - dominance check
        - categorical health flag
    """
    non_null = series.dropna()
    
    if len(non_null) == 0:
        return {
            "type": "categorical",
            "unique_count": 0,
            "top_values": [],
            "diversity_indicator": "no_data",
            "dominance_detected": False,
            "health_flag": "poor"
        }
    
    try:
        unique_count = non_null.nunique()
        value_counts = non_null.value_counts()
        
        # Top-k values with frequencies
        top_k = min(MAX_TOP_CATEGORIES, len(value_counts))
        top_values = []
        for value, count in value_counts.head(top_k).items():
            frequency = count / len(non_null)
            top_values.append({
                "value": str(value),
                "count": int(count),
                "frequency": round(frequency, 4)
            })
        
        # Dominance check
        if len(top_values) > 0:
            top_frequency = top_values[0]["frequency"]
            dominance_detected = top_frequency >= DOMINANCE_THRESHOLD
            dominant_value = top_values[0]["value"] if dominance_detected else None
        else:
            dominance_detected = False
            dominant_value = None
        
        # Diversity indicator using entropy-like measure
        if unique_count == 1:
            diversity_indicator = "no_diversity"
        elif unique_count <= 3:
            diversity_indicator = "low_diversity"
        elif unique_count <= 10:
            diversity_indicator = "medium_diversity"
        else:
            diversity_indicator = "high_diversity"
        
        # Health flag
        if dominance_detected and top_frequency > 0.95:
            health_flag = "poor"  # Almost all same value
        elif unique_count == len(non_null):
            health_flag = "weak"  # All unique (might be ID column)
        elif dominance_detected:
            health_flag = "weak"  # Single value dominates
        else:
            health_flag = "good"
        
        return {
            "type": "categorical",
            "unique_count": int(unique_count),
            "top_values": top_values,
            "diversity_indicator": diversity_indicator,
            "dominance_detected": dominance_detected,
            "dominant_value": dominant_value,
            "health_flag": health_flag
        }
        
    except Exception as e:
        logger.warning(f"Failed to profile categorical column {column_name}: {str(e)}")
        return {
            "type": "categorical",
            "error": str(e),
            "health_flag": "poor"
        }


def profile_column(series: pd.Series, column_name: str) -> Dict[str, Any]:
    """
    Generate comprehensive profile for a single column.
    
    Returns unified profile with:
    - Basic metadata (type, counts, quality)
    - Type-specific analytics
    - Sample values
    """
    total_count = len(series)
    null_count = int(series.isna().sum())
    non_null_count = total_count - null_count
    missing_ratio = null_count / total_count if total_count > 0 else 1.0
    
    # Detect column type
    column_type = detect_column_type(series, column_name)
    
    # Get unique count (bounded for performance)
    try:
        if non_null_count > 0:
            unique_count = int(series.nunique())
            unique_ratio = unique_count / non_null_count if non_null_count > 0 else 0
        else:
            unique_count = 0
            unique_ratio = 0
    except Exception:
        unique_count = None
        unique_ratio = 0
    
    # Sample values (bounded)
    sample_values = []
    if non_null_count > 0:
        try:
            samples = series.dropna().head(MAX_SAMPLE_VALUES).tolist()
            sample_values = [str(v)[:100] for v in samples]  # Truncate long values
        except Exception:
            sample_values = []
    
    # Assess data quality
    quality_flag = assess_data_quality(missing_ratio, unique_ratio, column_type)
    
    # Base profile
    profile = {
        "column_name": column_name,
        "type": column_type,
        "total_count": total_count,
        "non_null_count": non_null_count,
        "null_count": null_count,
        "missing_ratio": round(missing_ratio, 4),
        "unique_count": unique_count,
        "sample_values": sample_values,
        "quality_flag": quality_flag
    }
    
    # Add type-specific analytics
    if column_type == "numeric" and non_null_count >= MIN_ROWS_FOR_STATS:
        numeric_profile = profile_numeric_column(series, column_name)
        profile["numeric_stats"] = numeric_profile
    elif column_type == "categorical" and non_null_count > 0:
        categorical_profile = profile_categorical_column(series, column_name)
        profile["categorical_stats"] = categorical_profile
    
    return profile


def generate_narrative_insights(
    profiles: List[Dict[str, Any]],
    row_count: int,
    column_count: int
) -> Dict[str, Any]:
    """
    Generate lightweight narrative insights (rule-based, deterministic).
    
    Returns:
        - summary_text: Human-readable summary
        - confidence_level: high | medium | low
        - warnings: List of data quality warnings
    """
    warnings = []
    signals = []
    
    # Count column types
    type_counts = Counter(p["type"] for p in profiles)
    quality_counts = Counter(p["quality_flag"] for p in profiles)
    
    # Check for data quality issues
    high_missing_columns = sum(1 for p in profiles if p["missing_ratio"] > HIGH_MISSING_RATIO)
    poor_quality_columns = quality_counts.get("poor", 0)
    
    if high_missing_columns > 0:
        warnings.append(f"{high_missing_columns} column(s) have >50% missing values")
    
    if poor_quality_columns > 0:
        warnings.append(f"{poor_quality_columns} column(s) have poor data quality")
    
    # Check for numeric columns with issues
    numeric_profiles = [p for p in profiles if p["type"] == "numeric" and "numeric_stats" in p]
    if numeric_profiles:
        outlier_columns = [p["column_name"] for p in numeric_profiles 
                          if p["numeric_stats"].get("outlier_indicator") == "outliers_detected"]
        if outlier_columns:
            signals.append(f"Outliers detected in {len(outlier_columns)} numeric column(s)")
        
        highly_variable = [p["column_name"] for p in numeric_profiles
                          if p["numeric_stats"].get("stability_flag") == "highly_variable"]
        if highly_variable:
            signals.append(f"{len(highly_variable)} column(s) show high variability")
    
    # Check for categorical dominance
    categorical_profiles = [p for p in profiles if p["type"] == "categorical" and "categorical_stats" in p]
    if categorical_profiles:
        dominated_columns = [p["column_name"] for p in categorical_profiles
                            if p["categorical_stats"].get("dominance_detected")]
        if dominated_columns:
            warnings.append(f"{len(dominated_columns)} categorical column(s) dominated by single value")
    
    # Build summary text
    summary_parts = [
        f"Dataset contains {row_count} rows across {column_count} columns."
    ]
    
    if type_counts:
        type_summary = ", ".join([f"{count} {type_name}" for type_name, count in type_counts.most_common()])
        summary_parts.append(f"Column types: {type_summary}.")
    
    if signals:
        summary_parts.append(" ".join(signals) + ".")
    
    if warnings:
        summary_parts.append("Data quality concerns detected.")
    else:
        summary_parts.append("Data quality appears acceptable.")
    
    summary_text = " ".join(summary_parts)
    
    # Determine confidence level
    if row_count < MIN_ROWS_FOR_FULL_PROFILE:
        confidence_level = "low"
    elif poor_quality_columns > column_count * 0.5:
        confidence_level = "low"
    elif warnings:
        confidence_level = "medium"
    else:
        confidence_level = "high"
    
    return {
        "summary_text": summary_text,
        "confidence_level": confidence_level,
        "warnings": warnings,
        "signals": signals
    }


def profile_csv_data(
    df: pd.DataFrame,
    source_name: str = "unknown"
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Main entry point for CSV profiling.
    
    Performs comprehensive profiling with graceful fallback behavior.
    
    Args:
        df: Pandas DataFrame to profile
        source_name: Name/identifier of the data source
        
    Returns:
        Tuple of (result_dict, telemetry_dict)
        
    Result structure:
        {
            "profile": {...},
            "insights": {...},
            "graceful": {...},
            "telemetry": {...}
        }
    """
    start_time = time.time()
    
    logger.info(f"Starting CSV profiling - source={source_name}, shape={df.shape}")
    
    # Initialize telemetry
    telemetry = {
        "routing": "csv_profiler",
        "source": source_name,
        "latency_ms": 0,
        "processing_mode": "full",
        "degradation_level": "none",
        "graceful_message": None,
        "fallback_reason": None,
        "user_action_hint": None
    }
    
    # Graceful fallback: Empty DataFrame
    if df.empty:
        logger.warning(f"Empty DataFrame provided - source={source_name}")
        result = {
            "profile": {
                "row_count": 0,
                "column_count": 0,
                "columns": []
            },
            "insights": {
                "summary_text": "Dataset is empty - no data to profile.",
                "confidence_level": "low",
                "warnings": ["Empty dataset"]
            }
        }
        telemetry.update({
            "processing_mode": "fallback",
            "degradation_level": "failed",
            "graceful_message": "This dataset is empty and cannot be profiled.",
            "fallback_reason": "empty_dataframe",
            "user_action_hint": "Verify the data source contains valid data.",
            "latency_ms": int((time.time() - start_time) * 1000)
        })
        return result, telemetry
    
    row_count = len(df)
    column_count = len(df.columns)
    
    # Graceful fallback: Only 1 row
    if row_count == 1:
        logger.warning(f"Insufficient rows for profiling - source={source_name}, rows={row_count}")
        result = {
            "profile": {
                "row_count": row_count,
                "column_count": column_count,
                "columns": []
            },
            "insights": {
                "summary_text": f"Dataset contains only {row_count} row - insufficient for statistical profiling.",
                "confidence_level": "low",
                "warnings": ["Insufficient data"]
            }
        }
        telemetry.update({
            "processing_mode": "fallback",
            "degradation_level": "fallback",
            "graceful_message": "This dataset has too few rows for meaningful statistical analysis.",
            "fallback_reason": "insufficient_rows",
            "user_action_hint": "Provide a dataset with at least 3 rows for basic profiling.",
            "latency_ms": int((time.time() - start_time) * 1000)
        })
        return result, telemetry
    
    # Graceful fallback: Extremely small dataset
    if row_count < MIN_ROWS_FOR_FULL_PROFILE:
        logger.info(f"Small dataset detected - limited profiling - source={source_name}, rows={row_count}")
        telemetry["processing_mode"] = "partial"
        telemetry["degradation_level"] = "mild"
        telemetry["graceful_message"] = "Dataset is very small - some statistical measures may not be reliable."
        telemetry["user_action_hint"] = "Consider providing more data for comprehensive profiling."
    
    # Profile each column
    logger.info(f"Profiling {column_count} columns - source={source_name}")
    column_profiles = []
    failed_columns = []
    
    for col in df.columns:
        try:
            profile = profile_column(df[col], col)
            column_profiles.append(profile)
        except Exception as e:
            logger.error(f"Failed to profile column {col}: {str(e)}")
            failed_columns.append({
                "column_name": col,
                "error": str(e)
            })
    
    # Check if all columns failed
    if not column_profiles and failed_columns:
        logger.error(f"All columns failed to profile - source={source_name}")
        result = {
            "profile": {
                "row_count": row_count,
                "column_count": column_count,
                "columns": [],
                "failed_columns": failed_columns
            },
            "insights": {
                "summary_text": "Dataset profiling failed - all columns encountered errors.",
                "confidence_level": "low",
                "warnings": ["Profiling failed"]
            }
        }
        telemetry.update({
            "processing_mode": "failed",
            "degradation_level": "failed",
            "graceful_message": "Unable to profile this dataset due to data format issues.",
            "fallback_reason": "all_columns_failed",
            "user_action_hint": "Check data format and encoding. Ensure CSV is properly formatted.",
            "latency_ms": int((time.time() - start_time) * 1000)
        })
        return result, telemetry
    
    # Generate narrative insights
    logger.info(f"Generating narrative insights - source={source_name}")
    try:
        insights = generate_narrative_insights(column_profiles, row_count, column_count)
    except Exception as e:
        logger.error(f"Failed to generate insights: {str(e)}")
        insights = {
            "summary_text": f"Dataset contains {row_count} rows and {column_count} columns. Insight generation encountered errors.",
            "confidence_level": "low",
            "warnings": ["Insight generation failed"]
        }
    
    # Build result
    result = {
        "profile": {
            "row_count": row_count,
            "column_count": column_count,
            "columns": column_profiles
        },
        "insights": insights
    }
    
    if failed_columns:
        result["profile"]["failed_columns"] = failed_columns
        logger.warning(f"Partial success - {len(failed_columns)} columns failed - source={source_name}")
        telemetry["processing_mode"] = "partial"
        if telemetry["degradation_level"] == "none":
            telemetry["degradation_level"] = "mild"
            telemetry["graceful_message"] = f"Profiling completed but {len(failed_columns)} column(s) encountered errors."
    
    # Finalize telemetry
    latency_ms = int((time.time() - start_time) * 1000)
    telemetry["latency_ms"] = latency_ms
    
    logger.info(
        f"CSV profiling complete - source={source_name}, "
        f"mode={telemetry['processing_mode']}, "
        f"columns={len(column_profiles)}, "
        f"latency={latency_ms}ms"
    )
    
    return result, telemetry
