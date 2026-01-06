"""
Core insights infrastructure for narrative formatting and convergence.
"""

from .narrative_formatter import (
    NarrativeInsight,
    format_narrative_insight,
    merge_narrative_insights,
    validate_narrative_insight
)

__all__ = [
    "NarrativeInsight",
    "format_narrative_insight",
    "merge_narrative_insights",
    "validate_narrative_insight"
]
