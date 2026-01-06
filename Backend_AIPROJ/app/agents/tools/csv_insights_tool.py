"""
CSV Insights Tool — Agent tool wrapper for CSV analysis.

Wraps existing CSV insights service without duplicating logic.
"""

from typing import Dict, Any
import pandas as pd
from app.agents.tools.base_tool import AgentTool, ToolMetadata
from app.analytics.csv_insights import generate_csv_insights
from app.core.telemetry import ensure_complete_telemetry
from app.core.logging import setup_logger

logger = setup_logger("INFO")


class CSVInsightsTool(AgentTool):
    """
    Tool for generating CSV insights.
    
    Wraps analytics.csv_insights.generate_csv_insights() with standardized interface.
    """
    
    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        return ToolMetadata(
            name="csv_insights",
            description="Generate analytical insights from CSV data. Provides statistical analysis, column profiles, data quality assessment, and optional LLM-powered narrative insights. Always returns deterministic results; LLM insights only when explicitly enabled.",
            inputs={
                "dataframe": {
                    "type": "object",
                    "description": "Pandas DataFrame to analyze",
                    "required": True
                },
                "enable_llm_insights": {
                    "type": "boolean",
                    "description": "Enable LLM-powered narrative insights (default False)",
                    "required": False,
                    "default": False
                },
                "dataset_name": {
                    "type": "string",
                    "description": "Optional dataset name for reporting",
                    "required": False
                },
                "mode": {
                    "type": "string",
                    "description": "Analysis mode: light (default) or full",
                    "required": False,
                    "default": "light",
                    "enum": ["light", "full"]
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "object",
                        "properties": {
                            "rows": {"type": "integer"},
                            "columns": {"type": "integer"}
                        }
                    },
                    "column_profiles": {"type": "object"},
                    "data_quality": {"type": "object"},
                    "llm_insights": {"type": "object"},
                    "narrative_insight": {"type": "object"}
                }
            },
            uses_llm=False,  # LLM optional, disabled by default
            category="data_analysis",
            supports_export=True,  # Output can be exported to md/pdf
            requires_document=False,  # Works with dataframes, not documents
            supports_batch=False,  # One dataframe at a time
            examples=[
                {
                    "input": {"dataframe": "<df>", "enable_llm_insights": False},
                    "description": "Analyze CSV with deterministic insights only"
                },
                {
                    "input": {"dataframe": "<df>", "enable_llm_insights": True, "mode": "full"},
                    "description": "Full analysis with LLM-powered insights"
                }
            ]
        )
    
    def execute(self, **kwargs) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Execute CSV insights generation.
        
        Args:
            dataframe: Pandas DataFrame to analyze
            enable_llm_insights: Whether to enable LLM insights
            dataset_name: Optional dataset name
            mode: Analysis mode (light or full)
            
        Returns:
            Tuple of (insights_result, telemetry)
        """
        dataframe = kwargs.get("dataframe")
        enable_llm_insights = kwargs.get("enable_llm_insights", False)
        dataset_name = kwargs.get("dataset_name", "dataset")
        mode = kwargs.get("mode", "light")
        
        # Validate dataframe
        if not isinstance(dataframe, pd.DataFrame):
            logger.error("Tool error: csv_insights - dataframe must be pandas DataFrame")
            telemetry = ensure_complete_telemetry({
                "routing_decision": "csv_insights_error",
                "fallback_triggered": True,
                "degradation_level": "failed",
                "graceful_message": "Invalid input: dataframe must be pandas DataFrame"
            })
            return {"error": "Invalid dataframe"}, telemetry
        
        logger.info(
            f"Tool execution: csv_insights - shape={dataframe.shape}, "
            f"llm_enabled={enable_llm_insights}, mode={mode}"
        )
        
        try:
            # Call existing service (no logic duplication)
            insights, telemetry = generate_csv_insights(
                dataframe=dataframe,
                enable_llm_insights=enable_llm_insights,
                dataset_name=dataset_name,
                mode=mode
            )
            
            # Ensure telemetry is complete
            telemetry = ensure_complete_telemetry(telemetry)
            telemetry["routing_decision"] = f"csv_insights_{mode}"
            
            logger.info(
                f"Tool success: csv_insights - "
                f"rows={insights['summary']['rows']}, "
                f"columns={insights['summary']['columns']}, "
                f"llm_used={telemetry.get('llm_used', False)}"
            )
            
            return insights, telemetry
            
        except Exception as e:
            logger.error(f"Tool error: csv_insights - {str(e)}")
            
            # Return graceful error with complete telemetry
            telemetry = ensure_complete_telemetry({
                "routing_decision": "csv_insights_error",
                "fallback_triggered": True,
                "degradation_level": "failed",
                "graceful_message": f"CSV analysis failed: {str(e)}"
            })
            
            result = {
                "summary": {"rows": 0, "columns": 0, "analysis_performed": False},
                "column_profiles": {},
                "data_quality": {},
                "error": str(e)
            }
            
            return result, telemetry


# Singleton instance
csv_insights_tool = CSVInsightsTool()
