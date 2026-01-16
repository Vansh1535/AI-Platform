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
    
    # Check if we have a meaningful answer
    # Look for negative patterns anywhere in the first 200 chars
    answer_lower = answer.lower()[:200]
    no_answer_patterns = ["no answer", "no relevant information", "not found", "couldn't find", "no information"]
    has_no_answer = any(pattern in answer_lower for pattern in no_answer_patterns)
    has_answer = used_chunks > 0 and answer and not has_no_answer
    
    # Build report
    report = f"""# RAG Answer Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Query**: {query}

---

## Answer

{answer}

"""
    
    # If no answer, provide helpful guidance
    if not has_answer:
        report += """
> **Why no answer?**  
> Your query didn't match any content in the uploaded documents. This could mean:
> - The information you're looking for isn't in your document library
> - Try rephrasing your question or using different keywords
> - Make sure relevant documents have been uploaded and processed

"""
    
    report += "---\n\n"
    
    # Add citations only if we have them
    if citations and has_answer:
        report += f"## Evidence & Citations\n\n**Sources Used**: {used_chunks} document chunks\n\n"
        report += "### Source Documents\n\n"
        for i, citation in enumerate(citations[:5], 1):  # Limit to top 5
            score = citation.get("score", citation.get("relevance_score", 0))
            # Handle None score
            if score is None:
                score = 0
            doc_id = citation.get("document_id", citation.get("chunk_id", f"doc_{i}"))
            content = citation.get("content", citation.get("text", citation.get("chunk", "")))
            source = citation.get("source", citation.get("filename", ""))
            
            report += f"**Source {i}** (Relevance: {score*100:.0f}%)\n"
            if source:
                report += f"- Document: {source}\n"
            
            if content:
                # Truncate long content
                display_content = content[:300] + "..." if len(content) > 300 else content
                report += f"- Excerpt: *{display_content}*\n"
            
            report += "\n"
    
    # Add technical details section only if requested or if there are meaningful metrics
    degradation_level = meta.get('degradation_level', 'none')
    graceful_message = meta.get('graceful_message', '')
    
    # Only show technical details if there's degradation or explicit telemetry
    show_tech_details = degradation_level not in ['none', None] or graceful_message
    
    if show_tech_details:
        report += "---\n\n## Technical Details\n\n"
        
        # Ensure complete telemetry
        from app.core.telemetry import ensure_complete_telemetry
        meta = ensure_complete_telemetry(meta)
        
        # Performance
        if meta.get('latency_ms_total', 0) > 0:
            report += "### Performance\n\n"
            report += f"- **Total Time**: {meta.get('latency_ms_total', 0)}ms\n"
            if meta.get('latency_ms_retrieval', 0) > 0:
                report += f"- **Search Time**: {meta['latency_ms_retrieval']}ms\n"
            if meta.get('latency_ms_llm', 0) > 0:
                report += f"- **Processing Time**: {meta['latency_ms_llm']}ms\n"
            report += "\n"
        
        # Only show degradation if it exists
        if degradation_level not in ['none', None]:
            report += "### System Status\n\n"
            report += f"- **Status**: {degradation_level}\n"
            if graceful_message:
                report += f"\n> {graceful_message}\n"
    
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
    document_name = payload.get("document_name", payload.get("filename", "Unknown"))
    mode = payload.get("mode", "hybrid")
    meta = payload.get("meta", {})
    
    report = f"""# Document Summary Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Document**: {document_name}  
**Mode**: {mode}

---

## Summary

{summary}

---

"""
    
    # Only add technical details if there's degradation or issues
    degradation_level = meta.get('degradation_level', 'none')
    graceful_message = meta.get('graceful_message', '')
    
    if degradation_level not in ['none', None] or graceful_message:
        report += "\n## Technical Details\n\n"
        
        # Ensure complete telemetry
        from app.core.telemetry import ensure_complete_telemetry
        meta = ensure_complete_telemetry(meta)
        
        # Performance metrics
        if meta.get('latency_ms_total', 0) > 0:
            report += "### Performance\n\n"
            report += f"- **Total Time**: {meta.get('latency_ms_total', 0)}ms\n"
            if meta.get('latency_ms_retrieval', 0) > 0:
                report += f"- **Retrieval**: {meta['latency_ms_retrieval']}ms\n"
            if meta.get('latency_ms_llm', 0) > 0:
                report += f"- **Processing**: {meta['latency_ms_llm']}ms\n"
            report += "\n"
        
        # System status
        report += "### System Status\n\n"
        report += f"- **Status**: {degradation_level}\n"
        
        if graceful_message:
            report += f"\n> {graceful_message}\n"
    
    return report


def build_csv_insights_report(payload: Dict[str, Any]) -> str:
    """
    Generate Markdown report for CSV insights.
    
    Args:
        payload: CSV insights response with summary, column_profiles, data_quality, meta
        
    Returns:
        Markdown formatted report
    """
    try:
        dataset_name = payload.get("document_name", payload.get("dataset_name", "Unknown Dataset"))
        summary = payload.get("summary", {})
        meta = payload.get("meta", {})
        
        # Extract insights data from new structure
        row_count = summary.get("rows", 0)
        column_count = summary.get("columns", 0)
        numeric_columns = summary.get("numeric_columns", 0)
        categorical_columns = summary.get("categorical_columns", 0)
        column_profiles = payload.get("column_profiles", {})
        data_quality = payload.get("data_quality", {})
        llm_insights = payload.get("llm_insights")
        
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
            if patterns and isinstance(patterns, list):
                report += "### Key Patterns\n\n"
                for pattern in patterns:
                    pattern_str = str(pattern) if not isinstance(pattern, str) else pattern
                    report += f"- {pattern_str}\n"
                report += "\n"
            
            # Relationships
            relationships = llm_insights.get("relationships", [])
            if relationships and isinstance(relationships, list):
                report += "### Relationships\n\n"
                for rel in relationships:
                    rel_str = str(rel) if not isinstance(rel, str) else rel
                    report += f"- {rel_str}\n"
                report += "\n"
            
            # Outliers and risks
            risks = llm_insights.get("outliers_and_risks", [])
            if risks and isinstance(risks, list):
                report += "### ⚠️ Outliers & Risks\n\n"
                for risk in risks:
                    risk_str = str(risk) if not isinstance(risk, str) else risk
                    report += f"- {risk_str}\n"
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
        quality_flags = data_quality.get("quality_flags", data_quality.get("flags", []))
        
        report += f"- **Missing Data**: {null_ratio * 100:.1f}%\n"
        report += f"- **Duplicate Rows**: {duplicate_ratio * 100:.1f}%\n"
        
        if quality_flags:
            # Ensure all flags are strings
            flag_strings = [str(flag) if not isinstance(flag, str) else flag for flag in quality_flags]
            report += f"- **Quality Flags**: {', '.join(flag_strings)}\n"
        
        # Only add technical details if there's degradation or issues
        degradation_level = meta.get('degradation_level', 'none')
        graceful_message = meta.get('graceful_message', '')
        
        if degradation_level not in ['none', None] or graceful_message:
            report += f"\n---\n\n## Technical Details\n\n"
            
            # Ensure complete telemetry
            from app.core.telemetry import ensure_complete_telemetry
            meta = ensure_complete_telemetry(meta)
            
            # Performance metrics
            if meta.get('latency_ms_total', 0) > 0:
                report += "### Performance\n\n"
                report += f"- **Total Time**: {meta.get('latency_ms_total', 0)}ms\n"
                if meta.get('latency_ms_llm', 0) > 0:
                    report += f"- **Processing Time**: {meta['latency_ms_llm']}ms\n"
                report += "\n"
            
            # System status
            report += "### System Status\n\n"
            report += f"- **Status**: {degradation_level}\n"
            
            if graceful_message:
                report += f"\n> {graceful_message}\n"
        
        return report
    except Exception as e:
        logger.error(f"CSV report failed: {str(e)}")
        raise


def build_aggregation_report(payload: Dict[str, Any]) -> str:
    """
    Generate Markdown report for cross-file aggregated insights.
    
    Args:
        payload: Aggregation response with per_document and aggregated_insights
        
    Returns:
        Markdown formatted report
    """
    # Handle both "per_document" (new API) and "document_summaries" (legacy)
    document_summaries = payload.get("per_document", payload.get("document_summaries", []))
    aggregated = payload.get("aggregated_insights", {})
    failed_docs = payload.get("failed_documents") or []  # Handle None
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
        doc_name = doc.get("document_name", doc_id)
        doc_summary = doc.get("summary", "No summary available")
        
        report += f"### Document {i}: {doc_name}\n\n"
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
    
    # Only show technical details if there's degradation or failures
    degradation_level = meta.get('degradation_level', 'none')
    graceful_message = meta.get('graceful_message', '')
    has_failures = len(failed_docs) > 0
    
    if degradation_level not in ['none', None] or graceful_message or has_failures:
        report += "---\n\n## Technical Details\n\n"
        
        # Ensure complete telemetry
        from app.core.telemetry import ensure_complete_telemetry
        meta = ensure_complete_telemetry(meta)
        
        # Performance metrics if significant
        if meta.get('latency_ms_total', 0) > 0:
            report += "### Performance\n\n"
            report += f"- **Total Time**: {meta.get('latency_ms_total', 0)}ms\n"
            if meta.get('latency_ms_aggregation', 0) > 0:
                report += f"- **Aggregation**: {meta['latency_ms_aggregation']}ms\n"
            report += "\n"
        
        # Processing status
        report += "### Processing Status\n\n"
        report += f"- **Files Processed**: {meta.get('files_processed', len(document_summaries))}\n"
        if has_failures:
            report += f"- **Files Failed**: {len(failed_docs)}\n"
        report += f"- **Status**: {degradation_level}\n"
        
        if graceful_message:
            report += f"\n> {graceful_message}\n"
    
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
