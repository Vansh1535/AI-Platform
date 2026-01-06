"""
CSV LLM Insights — Phase 2

Extends CSV insights with optional LLM-powered narrative generation.
LLM operates on structured profiling output, not raw CSV data.

Key Features:
- Structured narrative insights from profiling data
- Confidence-controlled behavior (full/basic/fallback modes)
- Graceful degradation for weak signals or LLM failures
- Telemetry tracking for latency and fallback events
- Safety-first: never operates on raw rows, only summaries

Safety Contract:
1. LLM never sees raw CSV rows (privacy protection)
2. Always returns deterministic insights if LLM fails
3. Graceful degradation for small/weak datasets
4. Timeout protection (5s default)
5. Comprehensive telemetry for observability
"""

import json
import time
from typing import Dict, Any, Tuple, Optional
from app.core.logging import setup_logger
from app.utils.graceful_response import DegradationLevel
from app.llm.router import call_llm, is_llm_enabled

logger = setup_logger("INFO")

# Thresholds for LLM insight mode
MIN_ROWS_FOR_LLM = 20  # Minimum dataset size for LLM insights
MIN_CONFIDENCE_FOR_LLM = 0.5  # Minimum confidence score
LLM_TIMEOUT_SECONDS = 5.0  # Timeout for LLM generation


def prepare_llm_context(
    summary: Dict[str, Any],
    column_profiles: Dict[str, Any],
    data_quality: Dict[str, Any]
) -> str:
    """
    Prepare structured context for LLM from CSV profiling data.
    
    PRIVACY SAFE: Only includes aggregate statistics, never raw rows.
    
    Args:
        summary: Dataset summary (rows, columns, types)
        column_profiles: Column-level statistics
        data_quality: Data quality metrics
        
    Returns:
        JSON string with structured profiling data
    """
    # Extract numeric column statistics
    numeric_columns = {}
    categorical_columns = {}
    
    for col_name, profile in column_profiles.items():
        col_type = profile.get("type")
        
        if col_type in ["numeric", "categorical_numeric"]:
            numeric_columns[col_name] = {
                "mean": profile.get("mean"),
                "median": profile.get("median"),
                "std": profile.get("std"),
                "min": profile.get("min"),
                "max": profile.get("max"),
                "null_count": profile.get("null_count"),
                "variance": profile.get("variance")
            }
        elif col_type in ["categorical", "text"]:
            categorical_columns[col_name] = {
                "unique_values": profile.get("unique_count"),
                "top_values": profile.get("top_values", []),
                "null_count": profile.get("null_count")
            }
    
    # Build structured context
    context = {
        "dataset_summary": {
            "total_rows": summary.get("rows"),
            "total_columns": summary.get("columns"),
            "numeric_columns": summary.get("numeric_columns", 0),
            "categorical_columns": summary.get("categorical_columns", 0)
        },
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "data_quality": {
            "null_ratio": data_quality.get("null_ratio", 0),
            "duplicate_ratio": data_quality.get("duplicate_ratio", 0),
            "quality_flags": data_quality.get("flags", [])
        }
    }
    
    return json.dumps(context, indent=2)


def generate_llm_narrative_insights(
    summary: Dict[str, Any],
    column_profiles: Dict[str, Any],
    data_quality: Dict[str, Any],
    timeout: float = LLM_TIMEOUT_SECONDS
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Generate narrative insights using LLM analysis of structured profiling data.
    
    PRIVACY SAFE: LLM only sees aggregate statistics, never raw data.
    
    Args:
        summary: Dataset summary
        column_profiles: Column-level statistics
        data_quality: Data quality metrics
        timeout: Maximum time for LLM generation (seconds)
        
    Returns:
        Tuple of (insights_dict, telemetry_dict)
        
    Telemetry includes:
        - latency_ms_llm: Time spent in LLM generation
        - fallback_triggered: Whether fallback was used
        - routing_decision: "llm_full", "llm_basic", or "deterministic"
        - confidence_score: Confidence in LLM insights
        - degradation_level: Degradation state
    """
    start_time = time.time()
    
    telemetry = {
        "latency_ms_llm": 0,
        "fallback_triggered": False,
        "routing_decision": "llm_full",
        "confidence_score": 1.0,
        "degradation_level": "none",
        "fallback_reason": None,
        "graceful_message": None
    }
    
    try:
        # Check data size threshold
        total_rows = summary.get("rows", 0)
        if total_rows < MIN_ROWS_FOR_LLM:
            logger.info(f"Dataset too small for LLM insights: {total_rows} rows < {MIN_ROWS_FOR_LLM} minimum")
            telemetry["routing_decision"] = "deterministic"
            telemetry["fallback_triggered"] = True
            telemetry["fallback_reason"] = f"insufficient_data_{total_rows}_rows"
            telemetry["degradation_level"] = "fallback"
            telemetry["graceful_message"] = (
                f"Dataset is small ({total_rows} rows). Using basic narrative mode. "
                f"For AI-powered insights, provide datasets with at least {MIN_ROWS_FOR_LLM} rows."
            )
            
            # Return deterministic insights
            deterministic_insights = generate_deterministic_insights(
                summary, column_profiles, data_quality
            )
            telemetry["latency_ms_llm"] = int((time.time() - start_time) * 1000)
            return deterministic_insights, telemetry
        
        # Check data quality for weak signals
        null_ratio = data_quality.get("null_ratio", 0)
        quality_flags = data_quality.get("flags", [])
        
        if null_ratio > 0.7 or "analysis_error" in quality_flags:
            logger.info(f"Data quality too low for LLM insights: null_ratio={null_ratio}, flags={quality_flags}")
            telemetry["routing_decision"] = "deterministic"
            telemetry["fallback_triggered"] = True
            telemetry["fallback_reason"] = "low_data_quality"
            telemetry["degradation_level"] = "degraded"
            telemetry["graceful_message"] = (
                "Data quality is low (high missing values or errors). "
                "Using basic narrative mode. Consider data cleaning."
            )
            
            deterministic_insights = generate_deterministic_insights(
                summary, column_profiles, data_quality
            )
            telemetry["latency_ms_llm"] = int((time.time() - start_time) * 1000)
            return deterministic_insights, telemetry
        
        # Prepare structured context for LLM
        profiling_context = prepare_llm_context(summary, column_profiles, data_quality)
        
        # Build LLM prompt
        prompt = f"""You are a data analyst. Analyze this CSV dataset profile and provide structured insights.

DATASET PROFILING DATA (aggregate statistics only, no raw rows):
{profiling_context}

Generate a JSON response with these exact fields:
{{
  "dataset_explanation": "2-3 sentence overview of the dataset structure and content",
  "key_patterns": ["pattern 1", "pattern 2", "pattern 3"],
  "relationships": ["relationship observation 1", "relationship observation 2"],
  "outliers_and_risks": ["risk or outlier 1", "risk or outlier 2"],
  "data_quality_commentary": "1-2 sentences on data completeness and reliability"
}}

Keep each field concise. Focus on actionable insights. Be specific with numbers when relevant.
"""
        
        # Call LLM with timeout protection
        try:
            llm_response = call_llm(
                prompt=prompt,
                system="You are a data analyst specializing in CSV dataset analysis. Always respond with valid JSON.",
                temperature=0.3
            )
            
            llm_latency = int((time.time() - start_time) * 1000)
            telemetry["latency_ms_llm"] = llm_latency
            
            # Extract text from response
            response_text = llm_response.get('text', '')
            
            # Check if LLM is disabled
            if llm_response.get('provider') == 'none' or 'not enabled' in response_text.lower():
                logger.info("LLM provider not enabled, using deterministic insights")
                telemetry["routing_decision"] = "deterministic"
                telemetry["fallback_triggered"] = True
                telemetry["fallback_reason"] = "llm_provider_disabled"
                telemetry["degradation_level"] = "fallback"
                telemetry["graceful_message"] = "AI insights unavailable (LLM not configured). Using basic narrative mode."
                
                deterministic_insights = generate_deterministic_insights(
                    summary, column_profiles, data_quality
                )
                return deterministic_insights, telemetry
            
            # Parse LLM response
            try:
                # Handle markdown code blocks
                if response_text.startswith("```"):
                    # Remove markdown code block markers
                    response_text = response_text.split("```")[1]
                    if response_text.startswith("json"):
                        response_text = response_text[4:]
                    response_text = response_text.strip()
                
                llm_insights = json.loads(response_text)
                
                # Validate required fields
                required_fields = [
                    "dataset_explanation",
                    "key_patterns",
                    "relationships",
                    "outliers_and_risks",
                    "data_quality_commentary"
                ]
                
                if not all(field in llm_insights for field in required_fields):
                    raise ValueError(f"LLM response missing required fields: {required_fields}")
                
                # Successful LLM generation
                logger.info(f"LLM insights generated successfully in {llm_latency}ms")
                telemetry["routing_decision"] = "llm_full"
                telemetry["confidence_score"] = 0.9  # High confidence for valid LLM output
                
                result = {
                    "llm_insights": {
                        "enabled": True,
                        "mode": "full",
                        **llm_insights
                    }
                }
                
                return result, telemetry
                
            except (json.JSONDecodeError, ValueError) as parse_error:
                logger.warning(f"Failed to parse LLM response: {str(parse_error)}")
                telemetry["fallback_triggered"] = True
                telemetry["fallback_reason"] = f"llm_parse_error_{type(parse_error).__name__}"
                telemetry["degradation_level"] = "fallback"
                telemetry["graceful_message"] = "AI insights temporarily unavailable. Using basic narrative mode."
                
                deterministic_insights = generate_deterministic_insights(
                    summary, column_profiles, data_quality
                )
                return deterministic_insights, telemetry
                
        except TimeoutError:
            logger.warning(f"LLM generation timed out after {timeout}s")
            telemetry["latency_ms_llm"] = int(timeout * 1000)
            telemetry["fallback_triggered"] = True
            telemetry["fallback_reason"] = "llm_timeout"
            telemetry["degradation_level"] = "fallback"
            telemetry["routing_decision"] = "deterministic"
            telemetry["graceful_message"] = "AI analysis timed out. Using basic narrative mode."
            
            deterministic_insights = generate_deterministic_insights(
                summary, column_profiles, data_quality
            )
            return deterministic_insights, telemetry
            
        except Exception as llm_error:
            logger.error(f"LLM generation failed: {str(llm_error)}")
            telemetry["latency_ms_llm"] = int((time.time() - start_time) * 1000)
            telemetry["fallback_triggered"] = True
            telemetry["fallback_reason"] = f"llm_error_{type(llm_error).__name__}"
            telemetry["degradation_level"] = "fallback"
            telemetry["routing_decision"] = "deterministic"
            telemetry["graceful_message"] = "AI analysis temporarily unavailable. Using basic narrative mode."
            
            deterministic_insights = generate_deterministic_insights(
                summary, column_profiles, data_quality
            )
            return deterministic_insights, telemetry
            
    except Exception as e:
        logger.error(f"Unexpected error in LLM insight generation: {str(e)}")
        telemetry["latency_ms_llm"] = int((time.time() - start_time) * 1000)
        telemetry["fallback_triggered"] = True
        telemetry["fallback_reason"] = f"unexpected_error_{type(e).__name__}"
        telemetry["degradation_level"] = "failed"
        telemetry["routing_decision"] = "deterministic"
        telemetry["graceful_message"] = "Unable to generate insights. Analysis failed."
        
        # Return minimal deterministic insights
        result = {
            "llm_insights": {
                "enabled": False,
                "mode": "disabled",
                "dataset_explanation": "Dataset analysis unavailable due to an error.",
                "key_patterns": [],
                "relationships": [],
                "outliers_and_risks": [],
                "data_quality_commentary": "Unable to assess data quality."
            }
        }
        
        return result, telemetry


def generate_deterministic_insights(
    summary: Dict[str, Any],
    column_profiles: Dict[str, Any],
    data_quality: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate deterministic narrative insights from profiling data.
    
    Fallback mode when LLM is unavailable or data is too weak.
    Uses template-based generation from statistics.
    
    Args:
        summary: Dataset summary
        column_profiles: Column-level statistics
        data_quality: Data quality metrics
        
    Returns:
        Dictionary with deterministic insights
    """
    rows = summary.get("rows", 0)
    columns = summary.get("columns", 0)
    numeric_cols = summary.get("numeric_columns", 0)
    categorical_cols = summary.get("categorical_columns", 0)
    
    # Dataset explanation
    dataset_explanation = (
        f"This dataset contains {rows} rows and {columns} columns, "
        f"with {numeric_cols} numeric and {categorical_cols} categorical variables."
    )
    
    # Key patterns (from statistics)
    key_patterns = []
    
    # Find high-variance columns
    for col_name, profile in column_profiles.items():
        if profile.get("type") in ["numeric", "categorical_numeric"]:
            variance = profile.get("variance", 0)
            if variance and variance > 1000:
                key_patterns.append(f"{col_name} shows high variance (σ²={variance:.0f})")
    
    # Find columns with many unique values
    for col_name, profile in column_profiles.items():
        if profile.get("type") in ["categorical", "text"]:
            unique_count = profile.get("unique_count", 0)
            if unique_count > rows * 0.5:
                key_patterns.append(f"{col_name} has high cardinality ({unique_count} unique values)")
    
    if not key_patterns:
        key_patterns.append("Dataset has standard distribution patterns")
    
    # Relationships (simple correlations if available)
    relationships = []
    if numeric_cols >= 2:
        relationships.append(f"{numeric_cols} numeric columns available for correlation analysis")
    else:
        relationships.append("Limited numeric columns for relationship analysis")
    
    # Outliers and risks
    outliers_and_risks = []
    
    null_ratio = data_quality.get("null_ratio", 0)
    if null_ratio > 0.3:
        outliers_and_risks.append(f"High missing data rate: {null_ratio*100:.1f}% null values")
    
    duplicate_ratio = data_quality.get("duplicate_ratio", 0)
    if duplicate_ratio > 0.1:
        outliers_and_risks.append(f"Duplicate rows detected: {duplicate_ratio*100:.1f}%")
    
    if not outliers_and_risks:
        outliers_and_risks.append("No major data quality issues detected")
    
    # Data quality commentary
    quality_flags = data_quality.get("flags", [])
    if quality_flags:
        quality_commentary = f"Data quality flags: {', '.join(quality_flags)}. Consider data cleaning."
    else:
        quality_commentary = "Data appears complete and ready for analysis."
    
    return {
        "llm_insights": {
            "enabled": False,
            "mode": "basic",
            "dataset_explanation": dataset_explanation,
            "key_patterns": key_patterns[:3],  # Max 3 patterns
            "relationships": relationships[:2],  # Max 2 relationships
            "outliers_and_risks": outliers_and_risks[:2],  # Max 2 risks
            "data_quality_commentary": quality_commentary
        }
    }


def should_enable_llm_insights(
    summary: Dict[str, Any],
    data_quality: Dict[str, Any],
    confidence: float
) -> Tuple[bool, str]:
    """
    Determine if LLM insights should be enabled based on data characteristics.
    
    Args:
        summary: Dataset summary
        data_quality: Data quality metrics
        confidence: Confidence score from profiling
        
    Returns:
        Tuple of (should_enable, reason)
    """
    rows = summary.get("rows", 0)
    null_ratio = data_quality.get("null_ratio", 0)
    quality_flags = data_quality.get("flags", [])
    
    # Check minimum data size
    if rows < MIN_ROWS_FOR_LLM:
        return False, f"insufficient_data_{rows}_rows"
    
    # Check data quality
    if null_ratio > 0.7:
        return False, f"high_null_ratio_{null_ratio:.2f}"
    
    if "analysis_error" in quality_flags:
        return False, "analysis_error_present"
    
    # Check confidence
    if confidence < MIN_CONFIDENCE_FOR_LLM:
        return False, f"low_confidence_{confidence:.2f}"
    
    return True, "enabled"
