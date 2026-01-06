"""
Multi-File Insights Aggregator Tool (Phase C)

Agent-callable tool for cross-document analysis.
"""

import json
from typing import Dict, Any
from app.core.logging import setup_logger
from .aggregator_service import aggregate_insights

logger = setup_logger("INFO")


def aggregate_insights_tool(
    document_ids: str,  # JSON string or comma-separated
    mode: str = "auto",
    max_chunks: int = 5
) -> str:
    """
    Agent-callable tool for multi-document insights aggregation.
    
    Args:
        document_ids: JSON array string or comma-separated document IDs
                     e.g., '["doc1", "doc2"]' or "doc1,doc2,doc3"
        mode: Summarization mode (auto/extractive/hybrid)
        max_chunks: Maximum chunks per document
        
    Returns:
        Formatted string with per-document summaries and aggregated insights
    """
    logger.info(f"Aggregate insights tool called - IDs: {document_ids}, Mode: {mode}")
    
    try:
        # Parse document_ids
        if document_ids.strip().startswith('['):
            # JSON array format
            doc_list = json.loads(document_ids)
        else:
            # Comma-separated format
            doc_list = [doc_id.strip() for doc_id in document_ids.split(',')]
        
        # Validate
        if not doc_list:
            return "❌ Error: No document IDs provided. Please provide at least 2 document IDs."
        
        if len(doc_list) < 2:
            return (
                f"❌ Error: Need at least 2 documents for aggregation. "
                f"You provided {len(doc_list)}. "
                f"For single document summarization, use the summarize_document tool instead."
            )
        
        # Call service
        result, telemetry = aggregate_insights(
            document_ids=doc_list,
            mode=mode,
            max_chunks=max_chunks
        )
        
        # Format response
        output_parts = []
        
        # Header
        output_parts.append("=" * 80)
        output_parts.append("MULTI-DOCUMENT INSIGHTS AGGREGATION")
        output_parts.append("=" * 80)
        output_parts.append(f"Documents Processed: {telemetry['files_processed']}/{telemetry['files_requested']}")
        output_parts.append(f"Mode: {mode} | Hybrid Used: {telemetry['hybrid_used']}")
        output_parts.append("")
        
        # Per-document summaries
        output_parts.append("--- PER-DOCUMENT SUMMARIES ---")
        output_parts.append("")
        
        for i, doc_summary in enumerate(result['per_document'], 1):
            output_parts.append(f"[{i}] Document: {doc_summary['document_id']}")
            output_parts.append(f"    Mode: {doc_summary['mode_used']} | Confidence: {doc_summary['confidence']:.3f} | Chunks: {doc_summary['chunks_used']}")
            output_parts.append(f"    Summary: {doc_summary['summary'][:200]}...")
            output_parts.append("")
        
        # Failed documents (if any)
        if 'failed_documents' in result and result['failed_documents']:
            output_parts.append("--- FAILED DOCUMENTS ---")
            for failed in result['failed_documents']:
                output_parts.append(f"❌ {failed['document_id']}: {failed['error']}")
            output_parts.append("")
        
        # Aggregated insights
        if result.get('aggregated_insights'):
            insights = result['aggregated_insights']
            
            output_parts.append("=" * 80)
            output_parts.append("AGGREGATED CROSS-DOCUMENT INSIGHTS")
            output_parts.append("=" * 80)
            output_parts.append("")
            
            # Themes
            if insights.get('themes'):
                output_parts.append("🔍 KEY THEMES:")
                for theme in insights['themes'][:10]:
                    output_parts.append(f"   • {theme}")
                output_parts.append("")
            
            # Overlaps
            if insights.get('overlaps'):
                output_parts.append("🔗 OVERLAPPING THEMES (Cross-Document):")
                for overlap in insights['overlaps'][:7]:
                    docs_str = ", ".join(overlap['document_ids'][:3])
                    output_parts.append(f"   • {overlap['theme']} (in {overlap['frequency']} docs: {docs_str})")
                output_parts.append("")
            
            # Differences
            if insights.get('differences'):
                output_parts.append("🔀 UNIQUE ASPECTS PER DOCUMENT:")
                for diff in insights['differences'][:5]:
                    themes_str = ", ".join(diff['unique_themes'][:3])
                    output_parts.append(f"   • {diff['document_id']}: {themes_str}")
                output_parts.append("")
            
            # Entities
            if insights.get('entities'):
                output_parts.append("📋 KEY ENTITIES:")
                for entity in insights['entities'][:10]:
                    output_parts.append(f"   • {entity['entity']} (mentioned in {entity['frequency']} docs)")
                output_parts.append("")
            
            # Risk signals
            if insights.get('risk_signals'):
                output_parts.append("⚠️  RISK SIGNALS:")
                for risk in insights['risk_signals']:
                    terms_str = ", ".join(risk['risk_terms'][:5])
                    output_parts.append(f"   • {risk['document_id']}: {terms_str}")
                    for context in risk['contexts'][:2]:
                        output_parts.append(f"     → {context['context']}")
                output_parts.append("")
            
            # Semantic Clusters (NEW - non-breaking addition)
            if insights.get('semantic_clusters'):
                output_parts.append("🧩 SEMANTIC THEME CLUSTERS:")
                output_parts.append("   (Themes grouped by meaning, not wording)")
                output_parts.append("")
                
                for i, cluster in enumerate(insights['semantic_clusters'][:7], 1):
                    confidence_pct = int(cluster['confidence'] * 100)
                    member_count = cluster['member_count']
                    doc_count = len(cluster['documents_involved'])
                    
                    output_parts.append(f"   [{i}] {cluster['theme_label']}")
                    output_parts.append(f"       Confidence: {confidence_pct}% | Members: {member_count} | Docs: {doc_count}")
                    
                    # Show similar phrases in cluster
                    if member_count > 1:
                        other_members = [m for m in cluster['members'] if m != cluster['theme_label']][:3]
                        if other_members:
                            output_parts.append(f"       Similar: {', '.join(other_members)}")
                    
                    # Show evidence (if available)
                    if cluster.get('evidence'):
                        output_parts.append(f"       Evidence ({cluster['evidence_count']} sources):")
                        for evidence in cluster['evidence'][:2]:
                            preview = evidence['text_preview'][:100]
                            if len(evidence['text_preview']) > 100:
                                preview += "..."
                            output_parts.append(f"         • [{evidence['document_id']}] {preview}")
                            output_parts.append(f"           (similarity: {evidence['similarity']:.3f})")
                    
                    output_parts.append("")
            
            # LLM Synthesis (if available)
            if insights.get('llm_synthesis'):
                output_parts.append("💡 SYNTHESIS:")
                output_parts.append(insights['llm_synthesis'])
                output_parts.append(f"   (Generated by {insights.get('synthesis_provider', 'LLM')})")
                output_parts.append("")
        
        # Footer
        output_parts.append("=" * 80)
        output_parts.append(f"Total Processing Time: {telemetry['latency_ms_total']}ms")
        output_parts.append("=" * 80)
        
        return "\n".join(output_parts)
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return f"❌ Error: {str(e)}"
    
    except Exception as e:
        logger.error(f"Aggregation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"❌ Aggregation failed: {str(e)}"


def get_insights_tool_definition() -> Dict[str, Any]:
    """
    Get the tool definition for agent integration.
    
    Returns:
        Tool definition dict compatible with agent framework
    """
    return {
        "type": "function",
        "function": {
            "name": "aggregate_insights",
            "description": (
                "Aggregate insights across multiple documents. "
                "Provides per-document summaries and cross-document analysis including "
                "overlapping themes, unique aspects, entities, and risk signals. "
                "Use this when user asks to compare documents, analyze multiple files, "
                "or get combined insights from several sources. "
                "Requires at least 2 document IDs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "document_ids": {
                        "type": "string",
                        "description": (
                            "Document IDs to analyze. Can be JSON array string "
                            "(e.g., '[\"doc1\", \"doc2\"]') or comma-separated "
                            "(e.g., 'doc1,doc2,doc3'). Minimum 2 documents required."
                        )
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["auto", "extractive", "hybrid"],
                        "default": "auto",
                        "description": (
                            "Summarization mode: 'auto' (intelligent routing), "
                            "'extractive' (RAG-only, no LLM), 'hybrid' (RAG + LLM synthesis)"
                        )
                    },
                    "max_chunks": {
                        "type": "integer",
                        "default": 5,
                        "description": "Maximum chunks to retrieve per document (default: 5)"
                    }
                },
                "required": ["document_ids"]
            }
        }
    }
