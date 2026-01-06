"""
CSV Insights Foundation — Phase C Step 2 + PostgreSQL Cache

Provides basic analytical profiling for CSV datasets including:
- Descriptive statistics for numeric columns
- Category distribution for categorical columns  
- Data quality assessment (nulls, duplicates)
- Column type inference
- Extractive narrative insights
- PostgreSQL-backed caching for performance

No ML/AutoML dependencies — uses pandas only for runtime safety.
Follows graceful-messaging conventions for degraded cases.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import asyncio
import hashlib
from datetime import datetime, timedelta
from app.core.logging import setup_logger
from app.utils.graceful_response import graceful_fallback, success_message
from app.core.db import CSVCacheRepository
from app.core.db.graceful import safe_db_call

logger = setup_logger("INFO")

# Thresholds for data quality flags
MIN_ROWS_FOR_ANALYSIS = 10
MIN_NUMERIC_COLUMNS = 1
HIGH_NULL_RATIO = 0.5
HIGH_DUPLICATE_RATIO = 0.3
MAX_CATEGORIES_TO_SHOW = 10


def infer_column_types(df: pd.DataFrame) -> Dict[str, str]:
    """
    Infer semantic data types for each column.
    
    Args:
        df: Input dataframe
        
    Returns:
        Dictionary mapping column name to inferred type
    """
    column_types = {}
    
    for col in df.columns:
        dtype = df[col].dtype
        
        if pd.api.types.is_numeric_dtype(dtype):
            # Check if it's actually categorical despite being numeric
            unique_count = df[col].nunique()
            if unique_count <= 20 and len(df) > 50:
                column_types[col] = "categorical_numeric"
            else:
                column_types[col] = "numeric"
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            column_types[col] = "datetime"
        elif pd.api.types.is_bool_dtype(dtype):
            column_types[col] = "boolean"
        else:
            # String/object type - check if categorical
            unique_count = df[col].nunique()
            total_count = len(df)
            
            if unique_count <= 50 or (unique_count / total_count) < 0.5:
                column_types[col] = "categorical"
            else:
                column_types[col] = "text"
    
    return column_types


def compute_numeric_profile(df: pd.DataFrame, col: str) -> Dict[str, Any]:
    """
    Compute descriptive statistics for a numeric column.
    
    Args:
        df: Input dataframe
        col: Column name
        
    Returns:
        Dictionary with statistics
    """
    series = df[col].dropna()
    
    if len(series) == 0:
        return {
            "count": 0,
            "null_count": len(df),
            "mean": None,
            "median": None,
            "std": None,
            "min": None,
            "max": None,
            "q25": None,
            "q75": None
        }
    
    stats = {
        "count": int(series.count()),
        "null_count": int(df[col].isna().sum()),
        "mean": float(series.mean()),
        "median": float(series.median()),
        "std": float(series.std()),
        "min": float(series.min()),
        "max": float(series.max()),
        "q25": float(series.quantile(0.25)),
        "q75": float(series.quantile(0.75))
    }
    
    # Detect distribution skew
    if stats["std"] > 0:
        skewness = float(series.skew())
        if abs(skewness) > 1.0:
            stats["skew_note"] = "right-skewed" if skewness > 0 else "left-skewed"
    
    return stats


def compute_categorical_profile(df: pd.DataFrame, col: str) -> Dict[str, Any]:
    """
    Compute distribution summary for a categorical column.
    
    Args:
        df: Input dataframe
        col: Column name
        
    Returns:
        Dictionary with distribution info
    """
    series = df[col].dropna()
    value_counts = series.value_counts()
    
    profile = {
        "count": int(series.count()),
        "null_count": int(df[col].isna().sum()),
        "unique_values": int(df[col].nunique()),
        "top_categories": {}
    }
    
    # Get top categories (limit to prevent bloat)
    top_n = min(MAX_CATEGORIES_TO_SHOW, len(value_counts))
    for category, count in value_counts.head(top_n).items():
        profile["top_categories"][str(category)] = {
            "count": int(count),
            "percentage": round(float(count / len(series) * 100), 2)
        }
    
    # Flag if dominated by one category
    if len(value_counts) > 0:
        top_percentage = value_counts.iloc[0] / len(series)
        if top_percentage > 0.8:
            profile["dominance_note"] = f"Dominated by '{value_counts.index[0]}' ({top_percentage*100:.1f}%)"
    
    return profile


def assess_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Assess overall data quality of the dataset.
    
    Args:
        df: Input dataframe
        
    Returns:
        Dictionary with quality metrics
    """
    total_cells = df.shape[0] * df.shape[1]
    null_cells = df.isna().sum().sum()
    null_ratio = null_cells / total_cells if total_cells > 0 else 0
    
    # Duplicate detection
    duplicate_rows = df.duplicated().sum()
    duplicate_ratio = duplicate_rows / len(df) if len(df) > 0 else 0
    
    quality = {
        "total_rows": int(df.shape[0]),
        "total_columns": int(df.shape[1]),
        "total_cells": int(total_cells),
        "null_cells": int(null_cells),
        "null_ratio": round(float(null_ratio), 4),
        "duplicate_rows": int(duplicate_rows),
        "duplicate_ratio": round(float(duplicate_ratio), 4),
        "memory_usage_kb": round(float(df.memory_usage(deep=True).sum() / 1024), 2)
    }
    
    # Quality flags
    quality["flags"] = []
    
    if null_ratio > HIGH_NULL_RATIO:
        quality["flags"].append("high_missing_values")
    
    if duplicate_ratio > HIGH_DUPLICATE_RATIO:
        quality["flags"].append("high_duplicate_ratio")
    
    if df.shape[0] < MIN_ROWS_FOR_ANALYSIS:
        quality["flags"].append("small_dataset")
    
    if df.shape[1] > 50:
        quality["flags"].append("wide_table")
    
    return quality


def generate_narrative_insights(
    column_profiles: Dict[str, Any],
    column_types: Dict[str, str],
    data_quality: Dict[str, Any]
) -> str:
    """
    Generate extractive narrative summary from analytical results.
    
    Args:
        column_profiles: Column-wise profiles
        column_types: Inferred column types
        data_quality: Data quality metrics
        
    Returns:
        Human-readable insight summary
    """
    insights = []
    
    # Dataset size overview
    insights.append(
        f"The dataset contains {data_quality['total_columns']} columns "
        f"and {data_quality['total_rows']} rows."
    )
    
    # Column type distribution
    type_counts = {}
    for col_type in column_types.values():
        type_counts[col_type] = type_counts.get(col_type, 0) + 1
    
    type_summary = ", ".join([f"{count} {ctype}" for ctype, count in type_counts.items()])
    insights.append(f"Column types: {type_summary}.")
    
    # Numeric insights
    numeric_cols = [col for col, ctype in column_types.items() 
                    if ctype in ["numeric", "categorical_numeric"]]
    
    if numeric_cols:
        skewed_cols = []
        for col in numeric_cols:
            profile = column_profiles.get(col, {})
            if "skew_note" in profile:
                skewed_cols.append(f"{col} ({profile['skew_note']})")
        
        if skewed_cols:
            insights.append(f"Skewed distributions detected in: {', '.join(skewed_cols[:3])}.")
    
    # Categorical insights
    categorical_cols = [col for col, ctype in column_types.items() if ctype == "categorical"]
    
    if categorical_cols:
        dominant_cats = []
        for col in categorical_cols:
            profile = column_profiles.get(col, {})
            if "dominance_note" in profile:
                dominant_cats.append(col)
        
        if dominant_cats:
            insights.append(f"Dominant categories found in: {', '.join(dominant_cats[:2])}.")
    
    # Data quality notes
    if "high_missing_values" in data_quality["flags"]:
        insights.append(
            f"Note: {data_quality['null_ratio']*100:.1f}% of cells contain missing values."
        )
    
    if "high_duplicate_ratio" in data_quality["flags"]:
        insights.append(
            f"Note: {data_quality['duplicate_rows']} duplicate rows detected "
            f"({data_quality['duplicate_ratio']*100:.1f}%)."
        )
    
    return " ".join(insights)


def generate_csv_insights(
    dataframe: pd.DataFrame,
    file_meta: Optional[Dict[str, Any]] = None,
    mode: str = "light",
    enable_llm_insights: bool = False
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Generate analytical insights for a CSV dataset with PostgreSQL caching.
    
    Performs basic profiling including:
    - Descriptive statistics for numeric columns
    - Category distributions for categorical columns
    - Data quality assessment
    - Extractive narrative insights
    - Optional LLM-powered narrative (when enable_llm_insights=True)
    
    Caching Strategy:
    - Checks PostgreSQL cache before computation
    - Cache key: (file_hash, mode, enable_llm_insights)
    - Cache TTL: 24 hours
    - Graceful degradation if cache unavailable
    
    Follows graceful-messaging conventions for edge cases.
    
    Args:
        dataframe: Input pandas DataFrame
        file_meta: Optional metadata about the file (should include 'file_hash')
        mode: Analysis mode - "light" (default) or "full"
        enable_llm_insights: Enable optional LLM narrative synthesis (default False)
        
    Returns:
        Tuple of (insights_dict, telemetry_dict)
        
    Telemetry includes:
        - latency_ms_total: Total processing time
        - llm_used: Whether LLM was invoked
        - cache_hit: Whether result came from cache
        - fallback_triggered: Whether fallback logic was used
        - degradation_level: "none", "degraded", or "fallback"
        - graceful_message: User-facing message if degraded
        
    Example:
        >>> df = pd.read_csv("sales.csv")
        >>> # Deterministic mode (default)
        >>> insights, telemetry = generate_csv_insights(df, {"source": "sales.csv", "file_hash": "abc123..."})
        >>> # With LLM insights enabled
        >>> insights, telemetry = generate_csv_insights(df, {"source": "sales.csv", "file_hash": "abc123..."}, enable_llm_insights=True)
    """
    import time
    start_time = time.time()
    file_meta = file_meta or {}
    
    # Compute file hash if not provided
    file_hash = file_meta.get("file_hash")
    if not file_hash:
        # Generate hash from DataFrame content
        df_str = dataframe.to_csv(index=False)
        file_hash = hashlib.sha256(df_str.encode()).hexdigest()
        file_meta["file_hash"] = file_hash
    
    logger.info(
        f"Starting CSV insights generation - "
        f"Shape: {dataframe.shape}, Mode: {mode}, LLM: {enable_llm_insights}, Source: {file_meta.get('source', 'unknown')}, Hash: {file_hash[:16]}..."
    )
    
    # Initialize telemetry with required observability fields
    telemetry = {
        "routing": "csv_insights",
        "mode": mode,
        "source": file_meta.get("source"),
        "rows": dataframe.shape[0],
        "columns": dataframe.shape[1],
        "file_hash": file_hash[:16] + "...",  # Abbreviated for logs
        "latency_ms_total": 0,
        "llm_used": False,
        "cache_hit": False,
        "cache_checked": False,
        "fallback_triggered": False,
        "degradation_level": "none",
        "graceful_message": None
    }
    
    # Step 1: Check PostgreSQL metadata cache (if document_id provided and not in async context)
    document_id = file_meta.get("document_id") if file_meta else None
    metadata_from_db = None
    
    if document_id:
        try:
            # First check if we're in an async context
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Already in async context - skip metadata check
                    logger.debug("ℹ️ Async context detected - skipping PostgreSQL metadata check (use async version)")
                    telemetry["metadata_db_skipped"] = True
                    metadata_from_db = None
                else:
                    # No running loop - can use asyncio.run()
                    from app.analytics.csv_metadata import load_csv_metadata_from_db
                    metadata_from_db = asyncio.run(load_csv_metadata_from_db(document_id))
                    
                    if metadata_from_db:
                        logger.info(f"✅ CSV metadata loaded from PostgreSQL for document {document_id}")
                        telemetry["metadata_from_db"] = True
                    else:
                        logger.info(f"ℹ️ No CSV metadata in PostgreSQL for document {document_id} - will recompute")
                        telemetry["metadata_from_db"] = False
            except RuntimeError as e:
                if "There is no current event loop" in str(e):
                    # No event loop at all - safe to use asyncio.run()
                    from app.analytics.csv_metadata import load_csv_metadata_from_db
                    metadata_from_db = asyncio.run(load_csv_metadata_from_db(document_id))
                    if metadata_from_db:
                        logger.info(f"✅ CSV metadata loaded from PostgreSQL for document {document_id}")
                        telemetry["metadata_from_db"] = True
                    else:
                        logger.info(f"ℹ️ No CSV metadata in PostgreSQL for document {document_id} - will recompute")
                        telemetry["metadata_from_db"] = False
                else:
                    # Other RuntimeError - skip metadata check
                    logger.debug(f"ℹ️ Skipping metadata check: {str(e)}")
                    telemetry["metadata_db_skipped"] = True
                    
        except ImportError:
            logger.debug("ℹ️ CSV metadata module not available")
            telemetry["metadata_module_unavailable"] = True
        except Exception as e:
            logger.debug(f"ℹ️ Metadata check skipped: {type(e).__name__}")
            telemetry["metadata_db_skipped"] = True
            
        # Add telemetry defaults for cache behavior
        telemetry["cache_hit"] = False
        telemetry["cache_source"] = "computed"
        telemetry["latency_ms_cache_read"] = 0
        telemetry["latency_ms_compute"] = 0
    
    # Step 2: Check cache (with graceful degradation)
    try:
        # Check if we're in async context and can await directly
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In async context - skip cache for now (will be handled by endpoint)
                logger.debug("ℹ️ Cache check deferred to async endpoint context")
                telemetry["cache_checked"] = False
                telemetry["cache_deferred"] = True
            else:
                # Not in async context - can use asyncio.run()
                cache_entry = asyncio.run(
                    CSVCacheRepository.get_cached_insights(
                        file_hash=file_hash,
                        analysis_mode=mode,
                        enable_llm_insights=enable_llm_insights
                    )
                )
                telemetry["cache_checked"] = True
                
                if cache_entry:
                    logger.info(f"✅ Cache HIT for {file_hash[:16]}... (mode={mode}, llm={enable_llm_insights})")
                    telemetry["cache_hit"] = True
                    telemetry["latency_ms_total"] = int((time.time() - start_time) * 1000)
                    
                    # Return cached result
                    cached_result = cache_entry.insights_data
                    cached_telemetry = cache_entry.telemetry or telemetry
                    cached_telemetry.update({
                        "cache_hit": True,
                        "cache_access_count": cache_entry.access_count,
                        "cached_at": cache_entry.created_at.isoformat() if cache_entry.created_at else None,
                        "latency_ms_total": telemetry["latency_ms_total"]
                    })
                    
                    return cached_result, cached_telemetry
                else:
                    logger.info(f"❌ Cache MISS for {file_hash[:16]}... - computing fresh insights")
        except RuntimeError as inner_e:
            if "get_event_loop" in str(inner_e):
                # No event loop - safe to proceed
                logger.debug("ℹ️ No event loop detected - skipping cache")
                telemetry["cache_checked"] = False
                telemetry["no_event_loop"] = True
            else:
                raise  # Re-raise other RuntimeErrors
    
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e):
            logger.warning("⚠️ Cache skipped - in event loop context (use async version)")
            telemetry["cache_checked"] = False
            telemetry["cache_skipped"] = True
        else:
            logger.warning(f"⚠️ Cache check failed (degraded): {str(e)} - continuing without cache")
            telemetry["cache_degraded"] = True
            telemetry["cache_error"] = str(e)
    
    except Exception as e:
        logger.warning(f"⚠️ Cache check failed (degraded): {str(e)} - continuing without cache")
        telemetry["cache_degraded"] = True
        telemetry["cache_error"] = str(e)
    
    # Step 2: Compute insights (cache miss or cache unavailable)
    try:
        # Validate minimum dataset size
        if dataframe.shape[0] < MIN_ROWS_FOR_ANALYSIS:
            graceful_data = graceful_fallback(
                "csv_insufficient_data",
                reason=f"only_{dataframe.shape[0]}_rows",
                meta=telemetry
            )
            
            result = {
                "summary": {
                    "rows": dataframe.shape[0],
                    "columns": dataframe.shape[1],
                    "analysis_performed": False
                },
                "column_profiles": {},
                "data_quality": {"flags": ["small_dataset"]},
                "insight_notes": "Dataset has insufficient rows for meaningful analysis."
            }
            
            telemetry.update(graceful_data)
            logger.warning(f"Dataset too small for analysis: {dataframe.shape[0]} rows")
            
            # Add narrative format even for insufficient data
            try:
                from app.core.insights.narrative_formatter import format_narrative_insight
                result["narrative_insight"] = format_narrative_insight(
                    theme="Insufficient Data",
                    evidence=[f"Only {dataframe.shape[0]} rows available"],
                    source_documents=[file_meta.get("source", "CSV Dataset")],
                    confidence=0.0,
                    narrative_text=result["insight_notes"],
                    mode="deterministic"
                )
                telemetry["narrative_format_available"] = True
            except Exception:
                telemetry["narrative_format_available"] = False
            
            # Ensure complete telemetry before early return
            from app.core.telemetry import ensure_complete_telemetry
            telemetry = ensure_complete_telemetry(telemetry)
            
            return result, telemetry
        
        # Infer column types
        column_types = infer_column_types(dataframe)
        
        # Check for zero numeric columns
        numeric_cols = [col for col, ctype in column_types.items() 
                       if ctype in ["numeric", "categorical_numeric"]]
        
        if len(numeric_cols) == 0:
            graceful_data = graceful_fallback(
                "csv_no_variance",
                reason="zero_numeric_columns",
                meta=telemetry
            )
            
            result = {
                "summary": {
                    "rows": dataframe.shape[0],
                    "columns": dataframe.shape[1],
                    "numeric_columns": 0,
                    "analysis_performed": True
                },
                "column_profiles": {},
                "data_quality": assess_data_quality(dataframe),
                "insight_notes": "Dataset contains only text columns. No numeric analysis available."
            }
            
            telemetry.update(graceful_data)
            logger.info("No numeric columns found, returning basic profile only")
            
            return result, telemetry
        
        # Compute column profiles
        column_profiles = {}
        
        for col, col_type in column_types.items():
            try:
                if col_type in ["numeric", "categorical_numeric"]:
                    column_profiles[col] = {
                        "type": col_type,
                        **compute_numeric_profile(dataframe, col)
                    }
                elif col_type in ["categorical", "text"]:
                    column_profiles[col] = {
                        "type": col_type,
                        **compute_categorical_profile(dataframe, col)
                    }
                else:
                    # Basic profile for other types
                    column_profiles[col] = {
                        "type": col_type,
                        "count": int(dataframe[col].count()),
                        "null_count": int(dataframe[col].isna().sum())
                    }
            except Exception as e:
                logger.warning(f"Failed to profile column '{col}': {str(e)}")
                column_profiles[col] = {
                    "type": col_type,
                    "error": "profiling_failed"
                }
        
        # Assess data quality
        data_quality = assess_data_quality(dataframe)
        
        # Generate narrative insights (deterministic)
        insight_notes = generate_narrative_insights(
            column_profiles,
            column_types,
            data_quality
        )
        
        # Build result with deterministic insights
        result = {
            "summary": {
                "rows": data_quality["total_rows"],
                "columns": data_quality["total_columns"],
                "numeric_columns": len(numeric_cols),
                "categorical_columns": len([c for c in column_types.values() if c == "categorical"]),
                "analysis_performed": True
            },
            "column_profiles": column_profiles,
            "data_quality": data_quality,
            "insight_notes": insight_notes
        }
        
        # Optional LLM insights (only if enabled and LLM available)
        if enable_llm_insights:
            from app.analytics.csv_llm_insights import generate_llm_narrative_insights
            
            logger.info("LLM insights enabled - generating AI-powered narrative")
            telemetry["llm_used"] = True
            
            try:
                llm_insights, llm_telemetry = generate_llm_narrative_insights(
                    result["summary"], column_profiles, data_quality
                )
                
                # Add LLM insights to result (non-breaking extension)
                result["llm_insights"] = llm_insights.get("llm_insights")
                
                # Merge LLM telemetry
                if llm_telemetry:
                    telemetry["latency_ms_llm"] = llm_telemetry.get("latency_ms_llm", 0)
                    if llm_telemetry.get("fallback_triggered"):
                        telemetry["fallback_triggered"] = True
                        telemetry["degradation_level"] = llm_telemetry.get("degradation_level", "degraded")
                        telemetry["graceful_message"] = llm_telemetry.get("graceful_message")
                        
            except Exception as e:
                logger.warning(f"LLM insights generation failed: {str(e)} - continuing with deterministic results")
                telemetry["fallback_triggered"] = True
                telemetry["degradation_level"] = "degraded"
                telemetry["graceful_message"] = "AI insights unavailable. Showing statistical analysis only."
                result["llm_insights"] = {"enabled": False, "error": str(e)}
        else:
            logger.debug("LLM insights disabled - using deterministic mode only")
            result["llm_insights"] = {"enabled": False}
        
        # Calculate total latency
        telemetry["latency_ms_total"] = int((time.time() - start_time) * 1000)
        
        # Check for degraded quality (preserve existing logic)
        if data_quality["flags"]:
            if "high_missing_values" in data_quality["flags"]:
                graceful_data = graceful_fallback(
                    "csv_insufficient_data",
                    reason=f"high_null_ratio_{data_quality['null_ratio']:.2f}",
                    suggestion="Consider data cleaning or imputation before analysis.",
                    meta={"null_ratio": data_quality["null_ratio"]}
                )
                telemetry.update(graceful_data)
                if telemetry["degradation_level"] == "none":  # Don't override LLM degradation
                    telemetry["degradation_level"] = "mild"  # Override to mild since we have results
            else:
                # Minor flags, still successful
                graceful_data = success_message("csv_insights", {"flags": data_quality["flags"]})
                telemetry.update(graceful_data)
        else:
            # Full success
            graceful_data = success_message("csv_insights")
            telemetry.update(graceful_data)
        
        logger.info(
            f"CSV insights generation complete - {result['summary']['rows']} rows, {result['summary']['columns']} columns, "
            f"LLM: {telemetry['llm_used']}, Latency: {telemetry['latency_ms_total']}ms, "
            f"{len(column_profiles)} columns profiled, quality flags: {data_quality['flags']}"
        )
        
        # Add narrative format (optional, for export consistency)
        # This preserves backward compatibility while enabling narrative export
        try:
            from app.core.insights.narrative_formatter import convert_to_narrative_insight
            
            # Convert to narrative format for consistency
            narrative_insight = convert_to_narrative_insight(
                {
                    "key_pattern": insight_notes or "Data Analysis Complete",
                    "patterns": [f"{len(column_profiles)} columns analyzed"] + (
                        [result["llm_insights"].get("summary", "")] if result.get("llm_insights", {}).get("enabled") else []
                    ),
                    "dataset": file_meta.get("source", "CSV Dataset"),
                    "explanation": insight_notes,
                    "data_quality": data_quality
                },
                source_type="csv"
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
        
        # Step 3: Save to cache (with graceful degradation)
        if not telemetry.get("cache_hit") and not telemetry.get("cache_skipped"):  # Only save if not from cache and not skipped
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    logger.warning("⚠️ Cache save skipped - already in event loop (use async version)")
                    telemetry["cache_save_skipped"] = True
                else:
                    cache_ttl_hours = 24
                    expires_at = datetime.utcnow() + timedelta(hours=cache_ttl_hours)
                    
                    # Check if we're in async context
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # In async context - skip cache save
                            logger.debug("ℹ️ Cache save skipped - in event loop context")
                            telemetry["cache_save_skipped"] = True
                        else:
                            # Not in async context - can save
                            asyncio.run(
                                CSVCacheRepository.save_to_cache(
                                    file_hash=file_hash,
                                    analysis_mode=mode,
                                    enable_llm_insights=enable_llm_insights,
                                    insights_data=result,
                                    dataset_name=file_meta.get("source"),
                                    telemetry=telemetry,
                                    row_count=dataframe.shape[0],
                                    column_count=dataframe.shape[1],
                                    computation_time_ms=telemetry.get("latency_ms_total"),
                                    expires_at=expires_at
                                )
                            )
                            logger.info(f"✅ Saved insights to cache: {file_hash[:16]}... (TTL: {cache_ttl_hours}h)")
                            telemetry["cache_saved"] = True
                    except RuntimeError as e:
                        if "There is no current event loop" in str(e) or "cannot be called from a running event loop" in str(e):
                            logger.debug("ℹ️ Cache save skipped - event loop context")
                            telemetry["cache_save_skipped"] = True
                        else:
                            logger.debug(f"ℹ️ Cache save skipped: {str(e)}")
                            telemetry["cache_save_skipped"] = True
            
            except RuntimeError as e:
                if "cannot be called from a running event loop" in str(e):
                    logger.debug("ℹ️ Cache save skipped - in event loop context")
                    telemetry["cache_save_skipped"] = True
                else:
                    logger.debug(f"ℹ️ Cache operation skipped: {str(e)}")
                    telemetry["cache_save_skipped"] = True
            
            except Exception as e:
                logger.debug(f"ℹ️ Cache operation skipped: {str(e)}")
                telemetry["cache_save_skipped"] = True
        
        return result, telemetry
        
    except Exception as e:
        logger.error(f"CSV insights generation failed: {str(e)}")
        
        # Return graceful error
        from app.utils.graceful_response import graceful_failure
        graceful_data = graceful_failure(
            "csv_format_error",
            error=str(e),
            meta=telemetry
        )
        
        result = {
            "summary": {
                "rows": dataframe.shape[0] if hasattr(dataframe, 'shape') else 0,
                "columns": dataframe.shape[1] if hasattr(dataframe, 'shape') else 0,
                "analysis_performed": False
            },
            "column_profiles": {},
            "data_quality": {"flags": ["analysis_error"]},
            "insight_notes": "File could not be analyzed due to an error."
        }
        
        telemetry.update(graceful_data)
        
        return result, telemetry


# ============================================================================
# FUTURE-READY PLACEHOLDERS
# These are stubs for future Phase-C enhancements.
# They currently return "not enabled" messages but provide extension points.
# ============================================================================

def semantic_cluster_insights(datasets: list) -> Dict[str, Any]:
    """
    [PLACEHOLDER] Cross-dataset semantic clustering for theme discovery.
    
    Future feature: Identify common patterns and themes across multiple CSV files
    using semantic embeddings and clustering algorithms.
    
    Args:
        datasets: List of dataset dictionaries with insights
        
    Returns:
        Placeholder response indicating feature not yet enabled
    """
    logger.info("semantic_cluster_insights called - returning placeholder")
    
    return {
        "status": "not_enabled",
        "message": "Semantic clustering is not enabled yet — foundation mode only.",
        "available_in": "phase_c_step_3"
    }


def trend_anomaly_scan(dataframe: pd.DataFrame, time_column: Optional[str] = None) -> Dict[str, Any]:
    """
    [PLACEHOLDER] Time-series trend and anomaly detection.
    
    Future feature: Detect trends, seasonality, and anomalies in time-series data
    using statistical methods and outlier detection.
    
    Args:
        dataframe: Input DataFrame
        time_column: Name of the datetime column (optional)
        
    Returns:
        Placeholder response indicating feature not yet enabled
    """
    logger.info("trend_anomaly_scan called - returning placeholder")
    
    return {
        "status": "not_enabled",
        "message": "Trend and anomaly detection is not enabled yet — foundation mode only.",
        "available_in": "phase_c_step_4"
    }


def predictive_signal_preview(dataframe: pd.DataFrame, target_column: Optional[str] = None) -> Dict[str, Any]:
    """
    [PLACEHOLDER] Lightweight predictive signal analysis.
    
    Future feature: Quick preview of predictive potential using feature importance
    and correlation analysis, without full ML pipeline.
    
    Args:
        dataframe: Input DataFrame
        target_column: Name of the target variable (optional)
        
    Returns:
        Placeholder response indicating feature not yet enabled
    """
    logger.info("predictive_signal_preview called - returning placeholder")
    
    return {
        "status": "not_enabled",
        "message": "Predictive signal analysis is not enabled yet — foundation mode only.",
        "available_in": "phase_d_ml_pipeline"
    }
