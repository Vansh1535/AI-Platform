"""
Narrative Formatter — Unified narrative insight format across platform.

Convergence point for:
- CSV LLM insights
- Cross-file insights aggregation
- RAG + Summarizer export

Design Principles:
- Deterministic mode always works (no LLM required)
- LLM mode only runs when enable_llm_insights=True
- Never hallucinate — always reference evidence chunks
- Graceful fallback from LLM to deterministic
"""

from typing import Dict, Any, List, Optional, Literal
from dataclasses import dataclass, asdict
from datetime import datetime
from app.core.logging import setup_logger

logger = setup_logger("INFO")

# Valid insight modes
InsightMode = Literal["deterministic", "llm_hybrid"]


@dataclass
class NarrativeInsight:
    """
    Unified narrative insight structure.
    
    All platform insights (CSV, cross-file, RAG, summarizer) should
    produce this standardized format.
    """
    # Core narrative fields
    theme: str
    evidence: List[str]  # Evidence snippets/quotes
    confidence: float  # 0.0 to 1.0
    source_documents: List[str]  # Document IDs or sources
    narrative_text: str  # Human-readable narrative
    
    # Mode tracking
    mode: InsightMode  # "deterministic" or "llm_hybrid"
    
    # Optional enrichment
    related_themes: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = asdict(self)
        # Remove None values
        return {k: v for k, v in result.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NarrativeInsight":
        """Create from dictionary format."""
        return cls(
            theme=data["theme"],
            evidence=data["evidence"],
            confidence=data["confidence"],
            source_documents=data["source_documents"],
            narrative_text=data["narrative_text"],
            mode=data["mode"],
            related_themes=data.get("related_themes"),
            metadata=data.get("metadata")
        )


def format_narrative_insight(
    theme: str,
    evidence: List[str],
    source_documents: List[str],
    confidence: float = 0.0,
    narrative_text: Optional[str] = None,
    mode: InsightMode = "deterministic",
    related_themes: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format a narrative insight with standardized structure.
    
    Args:
        theme: Main theme/topic of the insight
        evidence: List of evidence snippets (quotes, data points)
        source_documents: List of source document IDs
        confidence: Confidence score 0.0 to 1.0
        narrative_text: Human-readable narrative (auto-generated if None)
        mode: "deterministic" or "llm_hybrid"
        related_themes: Optional related themes
        metadata: Optional additional metadata
        
    Returns:
        Standardized narrative insight dict
        
    Example:
        >>> insight = format_narrative_insight(
        ...     theme="Performance Optimization",
        ...     evidence=["System latency reduced by 40%", "Cache hit rate improved to 85%"],
        ...     source_documents=["doc_123", "doc_456"],
        ...     confidence=0.92,
        ...     mode="deterministic"
        ... )
    """
    # Auto-generate narrative if not provided
    if narrative_text is None:
        if len(evidence) == 1:
            narrative_text = f"{theme}: {evidence[0]}"
        else:
            narrative_text = f"{theme} (based on {len(evidence)} evidence points from {len(source_documents)} documents)"
    
    # Ensure confidence is in valid range
    confidence = max(0.0, min(1.0, confidence))
    
    insight = NarrativeInsight(
        theme=theme,
        evidence=evidence,
        confidence=confidence,
        source_documents=source_documents,
        narrative_text=narrative_text,
        mode=mode,
        related_themes=related_themes,
        metadata=metadata
    )
    
    return insight.to_dict()


def merge_narrative_insights(
    insights: List[Dict[str, Any]],
    merge_strategy: Literal["union", "intersection", "highest_confidence"] = "union"
) -> Dict[str, Any]:
    """
    Merge multiple narrative insights into a single insight.
    
    Args:
        insights: List of narrative insight dicts
        merge_strategy: How to merge:
            - "union": Combine all evidence
            - "intersection": Only common evidence
            - "highest_confidence": Take highest confidence insight
            
    Returns:
        Merged narrative insight
    """
    if not insights:
        return format_narrative_insight(
            theme="No insights",
            evidence=[],
            source_documents=[],
            confidence=0.0,
            mode="deterministic"
        )
    
    if len(insights) == 1:
        return insights[0]
    
    if merge_strategy == "highest_confidence":
        return max(insights, key=lambda x: x.get("confidence", 0.0))
    
    # Union or intersection merge
    all_evidence = []
    all_sources = []
    all_themes = []
    confidence_scores = []
    modes = []
    
    for insight in insights:
        all_evidence.extend(insight.get("evidence", []))
        all_sources.extend(insight.get("source_documents", []))
        all_themes.append(insight.get("theme", ""))
        confidence_scores.append(insight.get("confidence", 0.0))
        modes.append(insight.get("mode", "deterministic"))
    
    # Deduplicate
    unique_evidence = list(set(all_evidence))
    unique_sources = list(set(all_sources))
    unique_themes = list(set(filter(None, all_themes)))
    
    # Determine merged mode (llm_hybrid if any insight used LLM)
    merged_mode: InsightMode = "llm_hybrid" if "llm_hybrid" in modes else "deterministic"
    
    # Average confidence
    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
    
    # Create merged theme
    if len(unique_themes) == 1:
        merged_theme = unique_themes[0]
    else:
        merged_theme = f"Multiple themes: {', '.join(unique_themes[:3])}"
        if len(unique_themes) > 3:
            merged_theme += f" and {len(unique_themes) - 3} more"
    
    return format_narrative_insight(
        theme=merged_theme,
        evidence=unique_evidence,
        source_documents=unique_sources,
        confidence=avg_confidence,
        mode=merged_mode,
        related_themes=unique_themes if len(unique_themes) > 1 else None,
        metadata={
            "merged_from": len(insights),
            "merge_strategy": merge_strategy
        }
    )


def validate_narrative_insight(insight: Dict[str, Any]) -> bool:
    """
    Validate that an insight dict has all required fields.
    
    Args:
        insight: Narrative insight dict
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = [
        "theme",
        "evidence",
        "confidence",
        "source_documents",
        "narrative_text",
        "mode"
    ]
    
    # Check all required fields present
    if not all(field in insight for field in required_fields):
        missing = [f for f in required_fields if f not in insight]
        logger.warning(f"Narrative insight missing required fields: {missing}")
        return False
    
    # Validate types
    if not isinstance(insight["theme"], str):
        logger.warning("Narrative insight 'theme' must be string")
        return False
    
    if not isinstance(insight["evidence"], list):
        logger.warning("Narrative insight 'evidence' must be list")
        return False
    
    if not isinstance(insight["source_documents"], list):
        logger.warning("Narrative insight 'source_documents' must be list")
        return False
    
    if not isinstance(insight["confidence"], (int, float)):
        logger.warning("Narrative insight 'confidence' must be numeric")
        return False
    
    if insight["confidence"] < 0 or insight["confidence"] > 1:
        logger.warning("Narrative insight 'confidence' must be between 0 and 1")
        return False
    
    if insight["mode"] not in ["deterministic", "llm_hybrid"]:
        logger.warning("Narrative insight 'mode' must be 'deterministic' or 'llm_hybrid'")
        return False
    
    return True


def convert_to_narrative_insight(
    raw_insight: Dict[str, Any],
    source_type: Literal["csv", "rag", "summary", "aggregation"]
) -> Dict[str, Any]:
    """
    Convert legacy insight formats to standardized narrative format.
    
    Args:
        raw_insight: Raw insight in legacy format
        source_type: Type of source insight
        
    Returns:
        Standardized narrative insight
    """
    # Default values
    theme = "Insight"
    evidence = []
    source_documents = []
    confidence = 0.5
    mode: InsightMode = "deterministic"
    narrative_text = ""
    
    # Convert based on source type
    if source_type == "csv":
        theme = raw_insight.get("key_pattern", raw_insight.get("theme", "CSV Insight"))
        evidence = raw_insight.get("patterns", [])
        if "dataset" in raw_insight:
            source_documents = [raw_insight["dataset"]]
        confidence = 0.8  # CSV insights are deterministic
        narrative_text = raw_insight.get("explanation", raw_insight.get("narrative", ""))
        
    elif source_type == "rag":
        theme = raw_insight.get("answer", "")[:100]  # First 100 chars as theme
        evidence = [c.get("content", "")[:200] for c in raw_insight.get("citations", [])]
        source_documents = [c.get("document_id", "") for c in raw_insight.get("citations", [])]
        confidence = raw_insight.get("confidence", 0.5)
        narrative_text = raw_insight.get("answer", "")
        mode = "llm_hybrid" if raw_insight.get("used_llm", False) else "deterministic"
        
    elif source_type == "summary":
        theme = f"Summary of {raw_insight.get('document_id', 'document')}"
        evidence = [raw_insight.get("summary", "")]
        source_documents = [raw_insight.get("document_id", "")]
        confidence = raw_insight.get("confidence", 0.7)
        narrative_text = raw_insight.get("summary", "")
        mode = "llm_hybrid" if raw_insight.get("mode_used") == "hybrid" else "deterministic"
        
    elif source_type == "aggregation":
        theme = raw_insight.get("theme", "Aggregated Insight")
        evidence = raw_insight.get("evidence", raw_insight.get("overlaps", []))
        source_documents = raw_insight.get("documents", [])
        confidence = raw_insight.get("confidence", 0.6)
        narrative_text = raw_insight.get("summary", raw_insight.get("narrative", ""))
        mode = "llm_hybrid" if raw_insight.get("synthesis_used", False) else "deterministic"
    
    return format_narrative_insight(
        theme=theme,
        evidence=evidence,
        source_documents=source_documents,
        confidence=confidence,
        narrative_text=narrative_text,
        mode=mode,
        metadata={"source_type": source_type, "converted_from_legacy": True}
    )
