"""
Base Tool — Abstract base class for agent tools.

Provides standard interface for all agent tools.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod
from app.core.logging import setup_logger

logger = setup_logger("INFO")


@dataclass
class ToolMetadata:
    """
    Metadata describing an agent tool.
    
    Used for tool discovery, documentation, and UX support.
    Enriched to support tool classification and export capabilities.
    """
    name: str
    description: str
    inputs: Dict[str, Any]  # JSON schema for inputs
    output_schema: Dict[str, Any]  # JSON schema for outputs
    uses_llm: bool
    version: str = "1.0.0"
    category: Optional[str] = None
    examples: Optional[List[Dict[str, Any]]] = None
    supports_export: bool = True  # Whether tool output can be exported
    requires_document: bool = False  # Whether tool requires document context
    supports_batch: bool = False  # Whether tool supports batch processing
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "name": self.name,
            "description": self.description,
            "inputs": self.inputs,
            "output_schema": self.output_schema,
            "uses_llm": self.uses_llm,
            "version": self.version,
            "category": self.category,
            "examples": self.examples,
            "supports_export": self.supports_export,
            "requires_document": self.requires_document,
            "supports_batch": self.supports_batch
        }


class AgentTool(ABC):
    """
    Abstract base class for agent tools.
    
    All tools must implement:
    - execute(): Run the tool
    - get_metadata(): Return tool metadata
    """
    
    def __init__(self):
        """Initialize tool."""
        self.metadata = self.get_metadata()
        logger.info(f"Initialized agent tool: {self.metadata.name}")
    
    @abstractmethod
    def execute(self, **kwargs) -> tuple[Any, Dict[str, Any]]:
        """
        Execute the tool with given arguments.
        
        Args:
            **kwargs: Tool-specific arguments
            
        Returns:
            Tuple of (result, telemetry)
        """
        pass
    
    @abstractmethod
    def get_metadata(self) -> ToolMetadata:
        """
        Get tool metadata.
        
        Returns:
            ToolMetadata describing this tool
        """
        pass
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate tool inputs against schema.
        
        Args:
            inputs: Input arguments
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Basic validation - check required fields
        required_fields = []
        for field, schema in self.metadata.inputs.items():
            if schema.get("required", False):
                required_fields.append(field)
        
        missing = [f for f in required_fields if f not in inputs]
        if missing:
            return False, f"Missing required fields: {missing}"
        
        return True, None
    
    def __call__(self, **kwargs) -> tuple[Any, Dict[str, Any]]:
        """Allow tool to be called directly."""
        # Validate inputs
        is_valid, error = self.validate_inputs(kwargs)
        if not is_valid:
            from app.core.telemetry import ensure_complete_telemetry
            telemetry = ensure_complete_telemetry({
                "routing_decision": self.metadata.name,
                "fallback_triggered": True,
                "degradation_level": "failed",
                "graceful_message": f"Invalid inputs: {error}"
            })
            return {"error": error}, telemetry
        
        # Execute tool
        return self.execute(**kwargs)
