"""
Report Builder — Phase 3

Generates Markdown reports from various insight types (RAG, summaries, CSV insights, aggregations).
Provides clean, structured output with evidence links and scores.

Supports:
- RAG answers with citations
- Document summaries
- Cross-file aggregated insights
- CSV insights (with optional LLM insights)

Output: Clean Markdown with proper headings, lists, and formatting
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from app.core.logging import setup_logger

logger = setup_logger("INFO")


def build_rag_answer_report(payload: Dict[str, Any]) -> str:
    """
    Generate Markdown report for RAG answer.
    
    Args:
        payload: RAG answer response with answer, citations, metadata
        
    Returns:
        Markdown formatted report
        
    Example payload:
        {
            "answer": "Machine learning is...",
            "citations": [{"chunk_id": "...", "score": 0.85, ...}],
            "used_chunks": 5,
            "query": "What is machine learning?",
            "meta": {...}
        }
    """
    answer = payload.get("answer", "No answer generated")
    query = payload.get("query", payload.get("question", "Query not provided"))
    citations = payload.get("citations", [])
    used_chunks = payload.get("used_chunks", 0)
    meta = payload.get("meta", {})
    
    # Build report
    report = f"""# RAG Answer Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Query**: {query}

---

## Answer

{answer}

---

## Evidence & Citations

**Total Chunks Used**: {used_chunks}

"""
    
    # Add citations
    if citations:
        report += "### Source Documents\n\n"
        for i, citation in enumerate(citations, 1):
            score = citation.get("score", citation.get("relevance_score", 0))
            doc_id = citation.get("document_id", citation.get("chunk_id", f"doc_{i}"))
            content = citation.get("content", citation.get("text", ""))
            
            report += f"**Citation {i}** (Relevance: {score:.2f})\n"
            report += f"- Document ID: `{doc_id}`\n"
            
            if content:
                # Truncate long content
                display_content = content[:200] + "..." if len(content) > 200 else content
                report += f"- Excerpt: *{display_content}*\n"
            
            report += "\n"
    else:
        report += "*No citations available*\n\n"
    
    # Add metadata with comprehensive observability snapshot
    report += "---\n\n## Observability Snapshot\n\n"
    
    # Ensure complete telemetry
    from app.core.telemetry import ensure_complete_telemetry
    meta = ensure_complete_telemetry(meta)
    
    # Latency breakdown
    report += "### Performance\n\n"
    report += f"- **Total Latency**: {meta.get('latency_ms_total', 0)}ms\n"
    report += f"- **Retrieval**: {meta.get('latency_ms_retrieval', 0)}ms\n"
    report += f"- **Embedding**: {meta.get('latency_ms_embedding', 0)}ms\n"
    report += f"- **LLM**: {meta.get('latency_ms_llm', 0)}ms\n"
    
    # Routing and decision
    report += "\n### Routing & Decision\n\n"
    report += f"- **Routing**: {meta.get('routing_decision', 'N/A')}\n"
    report += f"- **Confidence**: {meta.get('confidence_score', 'N/A')}\n"
    report += f"- **Cache Hit**: {'Yes' if meta.get('cache_hit') else 'No'}\n"
    report += f"- **Retry Count**: {meta.get('retry_count', 0)}\n"
    
    # Degradation and resilience
    report += "\n### Resilience\n\n"
    report += f"- **Degradation Level**: {meta.get('degradation_level', 'none')}\n"
    report += f"- **Fallback Triggered**: {'Yes' if meta.get('fallback_triggered') else 'No'}\n"
    
    if meta.get('graceful_message'):
        report += f"\n> **Note**: {meta.get('graceful_message')}\n"
    
    return report


def build_summary_report(payload: Dict[str, Any]) -> str:
    """
    Generate Markdown report for document summary.
    
    Args:
        payload: Summary response with summary, metadata
        
    Returns:
        Markdown formatted report
    """
    summary = payload.get("summary", "No summary generated")
    document_id = payload.get("document_id", "Unknown")
    mode = payload.get("mode", "hybrid")
    meta = payload.get("meta", {})
    
    report = f"""# Document Summary Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Document ID**: `{document_id}`  
**Mode**: {mode}

---

## Summary

{summary}

---

## Analysis Details

"""
    
    # Add metadata with comprehensive observability snapshot
    report += f"\n---\n\n## Observability Snapshot\n\n"
    
    # Ensure complete telemetry
    from app.core.telemetry import ensure_complete_telemetry
    meta = ensure_complete_telemetry(meta)
    
    # Latency breakdown
    report += "### Performance\n\n"
    report += f"- **Total Latency**: {meta.get('latency_ms_total', 0)}ms\n"
    
    if meta.get('latency_ms_retrieval'):
        report += f"- **Retrieval**: {meta['latency_ms_retrieval']}ms\n"
    if meta.get('latency_ms_embedding'):
        report += f"- **Embedding**: {meta['latency_ms_embedding']}ms\n"
    if meta.get('latency_ms_llm'):
        report += f"- **LLM**: {meta['latency_ms_llm']}ms\n"
    
    # Routing and decision
    report += "\n### Routing & Decision\n\n"
    report += f"- **Routing**: {meta.get('routing_decision', 'N/A')}\n"
    report += f"- **Confidence**: {meta.get('confidence_score', 'N/A')}\n"
    report += f"- **Cache Hit**: {'Yes' if meta.get('cache_hit') else 'No'}\n"
    report += f"- **Retry Count**: {meta.get('retry_count', 0)}\n"
    
    # Degradation and resilience
    report += "\n### Resilience\n\n"
    report += f"- **Degradation Level**: {meta.get('degradation_level', 'none')}\n"
    report += f"- **Fallback Triggered**: {'Yes' if meta.get('fallback_triggered') else 'No'}\n"
    
    if meta.get('graceful_message'):
        report += f"\n> **Note**: {meta.get('graceful_message')}\n"
    
    return report


def build_csv_insights_report(payload: Dict[str, Any]) -> str:
    """
    Generate Markdown report for CSV insights.
    
    Args:
        payload: CSV insights response with dataset_name, insights, metadata
        
    Returns:
        Markdown formatted report
    """
    dataset_name = payload.get("dataset_name", "Unknown Dataset")
    insights = payload.get("insights", {})
    meta = payload.get("meta", {})
    
    # Extract insights data
    row_count = insights.get("row_count", 0)
    column_count = insights.get("column_count", 0)
    numeric_columns = insights.get("numeric_columns", 0)
    categorical_columns = insights.get("categorical_columns", 0)
    column_profiles = insights.get("column_profiles", {})
    data_quality = insights.get("data_quality", {})
    llm_insights = insights.get("llm_insights")
    
    report = f"""# CSV Insights Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Dataset**: `{dataset_name}`

---

## Dataset Overview

- **Rows**: {row_count:,}
- **Columns**: {column_count}
- **Numeric Columns**: {numeric_columns}
- **Categorical Columns**: {categorical_columns}

"""
    
    # Add LLM insights if available
    if llm_insights:
        report += "---\n\n## AI-Powered Insights\n\n"
        
        # Dataset explanation
        if llm_insights.get("dataset_explanation"):
            report += f"{llm_insights['dataset_explanation']}\n\n"
        
        # Key patterns
        patterns = llm_insights.get("key_patterns", [])
        if patterns:
            report += "### Key Patterns\n\n"
            for pattern in patterns:
                report += f"- {pattern}\n"
            report += "\n"
        
        # Relationships
        relationships = llm_insights.get("relationships", [])
        if relationships:
            report += "### Relationships\n\n"
            for rel in relationships:
                report += f"- {rel}\n"
            report += "\n"
        
        # Outliers and risks
        risks = llm_insights.get("outliers_and_risks", [])
        if risks:
            report += "### ⚠️ Outliers & Risks\n\n"
            for risk in risks:
                report += f"- {risk}\n"
            report += "\n"
        
        # Data quality
        if llm_insights.get("data_quality_commentary"):
            report += f"### Data Quality Commentary\n\n{llm_insights['data_quality_commentary']}\n\n"
    
    # Add deterministic/statistical analysis
    report += "---\n\n## Statistical Analysis\n\n"
    
    # Add column profiles
    if column_profiles:
        report += "### Column Profiles\n\n"
        for col_name, profile in column_profiles.items():
            col_type = profile.get("type", "unknown")
            report += f"**`{col_name}`** ({col_type})\n\n"
            
            if col_type == "numeric":
                report += f"- Mean: {profile.get('mean', 'N/A')}\n"
                report += f"- Median: {profile.get('median', 'N/A')}\n"
                report += f"- Std Dev: {profile.get('std', 'N/A')}\n"
                report += f"- Min: {profile.get('min', 'N/A')}\n"
                report += f"- Max: {profile.get('max', 'N/A')}\n"
            elif col_type == "categorical":
                report += f"- Unique Values: {profile.get('unique_values', 'N/A')}\n"
                
                top_values = profile.get("top_values", {})
                if top_values:
                    report += "- Top Values:\n"
                    for value, count in list(top_values.items())[:5]:
                        report += f"  - `{value}`: {count}\n"
            
            report += "\n"
    
    # Add data quality
    report += "---\n\n## Data Quality Assessment\n\n"
    null_ratio = data_quality.get("null_ratio", 0.0)
    duplicate_ratio = data_quality.get("duplicate_ratio", 0.0)
    quality_flags = data_quality.get("quality_flags", [])
    
    report += f"- **Missing Data**: {null_ratio * 100:.1f}%\n"
    report += f"- **Duplicate Rows**: {duplicate_ratio * 100:.1f}%\n"
    
    if quality_flags:
        report += f"- **Quality Flags**: {', '.join(quality_flags)}\n"
    
    # Add processing metadata with comprehensive observability snapshot
    report += f"\n---\n\n## Observability Snapshot\n\n"
    
    # Ensure complete telemetry
    from app.core.telemetry import ensure_complete_telemetry
    meta = ensure_complete_telemetry(meta)
    
    # Latency breakdown
    report += "### Performance\n\n"
    report += f"- **Total Latency**: {meta.get('latency_ms_total', 0)}ms\n"
    
    if meta.get('latency_ms_llm'):
        report += f"- **LLM Latency**: {meta['latency_ms_llm']}ms\n"
    
    # LLM usage
    report += "\n### LLM Usage\n\n"
    report += f"- **LLM Used**: {'Yes' if meta.get('llm_used') else 'No'}\n"
    
    if meta.get('enable_llm_insights') is not None:
        report += f"- **LLM Insights Enabled**: {'Yes' if meta['enable_llm_insights'] else 'No'}\n"
    
    # Degradation and resilience
    report += "\n### Resilience\n\n"
    report += f"- **Degradation Level**: {meta.get('degradation_level', 'none')}\n"
    report += f"- **Fallback Triggered**: {'Yes' if meta.get('fallback_triggered') else 'No'}\n"
    
    if meta.get('graceful_message'):
        report += f"\n> **Note**: {meta.get('graceful_message')}\n"
    
    return report
    report += "---\n\n## Data Quality Assessment\n\n"
    report += f"- **Missing Data**: {data_quality.get('null_ratio', 0)*100:.1f}%\n"
    report += f"- **Duplicate Rows**: {data_quality.get('duplicate_ratio', 0)*100:.1f}%\n"
    
    quality_flags = data_quality.get("flags", [])
    if quality_flags:
        report += "- **Quality Flags**: " + ", ".join(quality_flags) + "\n"
    
    # Add metadata
    report += "\n---\n\n## Processing Metadata\n\n"
    report += f"- **Latency**: {meta.get('latency_ms_total', 0)}ms\n"
    if meta.get('latency_ms_llm'):
        report += f"- **LLM Latency**: {meta.get('latency_ms_llm')}ms\n"
    report += f"- **Degradation Level**: {meta.get('degradation_level', 'none')}\n"
    
    return report


def build_aggregation_report(payload: Dict[str, Any]) -> str:
    """
    Generate Markdown report for cross-file aggregated insights.
    
    Args:
        payload: Aggregation response with document_summaries and aggregated_insights
        
    Returns:
        Markdown formatted report
    """
    document_summaries = payload.get("document_summaries", [])
    aggregated = payload.get("aggregated_insights", {})
    failed_docs = payload.get("failed_documents", [])
    meta = payload.get("meta", {})
    
    report = f"""# Cross-File Insights Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Documents Analyzed**: {len(document_summaries)}

---

## Aggregated Insights

"""
    
    # Add aggregated insights
    if aggregated:
        themes = aggregated.get("themes", [])
        if themes:
            report += "### Common Themes\n\n"
            for theme in themes:
                report += f"- {theme}\n"
            report += "\n"
        
        key_findings = aggregated.get("key_findings", [])
        if key_findings:
            report += "### Key Findings\n\n"
            for finding in key_findings:
                report += f"- {finding}\n"
            report += "\n"
        
        summary = aggregated.get("summary", "")
        if summary:
            report += f"### Overall Summary\n\n{summary}\n\n"
    
    # Add per-document summaries
    report += "---\n\n## Per-Document Summaries\n\n"
    for i, doc in enumerate(document_summaries, 1):
        doc_id = doc.get("document_id", f"doc_{i}")
        doc_summary = doc.get("summary", "No summary available")
        
        report += f"### Document {i}: `{doc_id}`\n\n"
        report += f"{doc_summary}\n\n"
    
    # Add failed documents if any
    if failed_docs:
        report += "---\n\n## Failed Documents\n\n"
        report += f"⚠️ {len(failed_docs)} document(s) could not be processed:\n\n"
        for failed in failed_docs:
            doc_id = failed.get("document_id", "Unknown")
            error = failed.get("error", "Unknown error")
            report += f"- `{doc_id}`: {error}\n"
        report += "\n"
    
    # Add metadata with comprehensive observability snapshot
    report += "---\n\n## Observability Snapshot\n\n"
    
    # Ensure complete telemetry
    from app.core.telemetry import ensure_complete_telemetry
    meta = ensure_complete_telemetry(meta)
    
    # Latency breakdown
    report += "### Performance\n\n"
    report += f"- **Total Latency**: {meta.get('latency_ms_total', 0)}ms\n"
    
    if meta.get('latency_ms_summarization'):
        report += f"- **Summarization**: {meta['latency_ms_summarization']}ms\n"
    if meta.get('latency_ms_aggregation'):
        report += f"- **Aggregation**: {meta['latency_ms_aggregation']}ms\n"
    if meta.get('latency_ms_clustering'):
        report += f"- **Clustering**: {meta['latency_ms_clustering']}ms\n"
    
    # Files and processing
    report += "\n### Processing\n\n"
    report += f"- **Files Processed**: {meta.get('files_processed', len(document_summaries))}\n"
    report += f"- **Files Failed**: {meta.get('files_failed', len(failed_docs))}\n"
    report += f"- **Routing**: {meta.get('routing', 'insight_aggregator')}\n"
    
    # Clustering and semantic features
    if meta.get('semantic_clustering_used'):
        report += "\n### Semantic Analysis\n\n"
        report += f"- **Clustering Used**: Yes\n"
        report += f"- **Cluster Count**: {meta.get('cluster_count', 0)}\n"
        report += f"- **Avg Cluster Confidence**: {meta.get('avg_cluster_confidence', 'N/A')}\n"
    
    # Degradation and resilience
    report += "\n### Resilience\n\n"
    report += f"- **Degradation Level**: {meta.get('degradation_level', 'none')}\n"
    report += f"- **Fallback Triggered**: {'Yes' if meta.get('fallback_triggered') else 'No'}\n"
    
    if meta.get('graceful_message'):
        report += f"\n> **Note**: {meta.get('graceful_message')}\n"
    
    return report


def build_generic_report(payload: Dict[str, Any], title: str = "Generic Report") -> str:
    """
    Generate generic Markdown report for unknown payload types.
    
    Args:
        payload: Any response payload
        title: Report title
        
    Returns:
        Markdown formatted report
    """
    report = f"""# {title}

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Data

"""
    
    # Render payload as formatted structure
    for key, value in payload.items():
        if key == "meta":
            continue  # Handle separately
        
        report += f"### {key.replace('_', ' ').title()}\n\n"
        
        if isinstance(value, (str, int, float, bool)):
            report += f"{value}\n\n"
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    report += f"- {item}\n"
                else:
                    report += f"- {item}\n"
            report += "\n"
        elif isinstance(value, dict):
            for k, v in value.items():
                report += f"- **{k}**: {v}\n"
            report += "\n"
    
    # Add metadata if present
    if "meta" in payload:
        meta = payload["meta"]
        report += "---\n\n## Metadata\n\n"
        for key, value in meta.items():
            if value is not None:
                report += f"- **{key.replace('_', ' ').title()}**: {value}\n"
    
    return report


def build_report(payload_source: str, payload: Dict[str, Any]) -> str:
    """
    Build Markdown report based on payload source type.
    
    Args:
        payload_source: Type of payload ("rag", "summary", "csv_insights", "aggregation")
        payload: The data payload
        
    Returns:
        Markdown formatted report
        
    Raises:
        ValueError: If payload_source is unknown
    """
    if payload_source == "rag":
        return build_rag_answer_report(payload)
    elif payload_source == "summary":
        return build_summary_report(payload)
    elif payload_source == "csv_insights":
        return build_csv_insights_report(payload)
    elif payload_source == "aggregation":
        return build_aggregation_report(payload)
    else:
        logger.warning(f"Unknown payload_source: {payload_source}, using generic report")
        return build_generic_report(payload, title="Generic Report")
