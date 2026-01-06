"""
Agent API routes for orchestrating RAG and ML capabilities.
Extended with decision transparency and user-facing messages.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from app.core.logging import setup_logger
from app.agents.workflows.simple_agent import get_agent
from app.utils.telemetry import TelemetryTracker, ComponentType, merge_telemetry
from app.utils.graceful_response import DegradationLevel

logger = setup_logger()

router = APIRouter()


class AgentRequest(BaseModel):
    """Request model for agent execution."""
    prompt: str = Field(..., description="Natural language prompt for the agent")
    max_iterations: int = Field(5, description="Maximum number of tool calls", ge=1, le=10)


class ToolExecution(BaseModel):
    """Model for tool execution trace."""
    iteration: int
    tool: str
    arguments: Dict[str, Any]
    result: str


class AgentMeta(BaseModel):
    """Model for legacy agent execution metadata (minimal)."""
    mode: Optional[str] = None
    provider: Optional[str] = None
    tool_used: Optional[str] = None
    latency_ms_total: Optional[int] = None
    error_class: Optional[str] = None
    safe_degraded_mode: Optional[bool] = None
    # RAG Transparency fields
    confidence_path: Optional[str] = None
    answer_status: Optional[str] = None
    retrieval_score_primary: Optional[float] = None


class ExtendedAgentMeta(BaseModel):
    """Model for extended agent execution metadata (verbose mode)."""
    # Decision routing
    decision_route: Optional[str] = None
    reason: Optional[str] = None
    tool_selected: Optional[str] = None
    tool_confidence: Optional[float] = None
    alternatives_considered: List[str] = []
    
    # Provider and execution
    provider_used: str = "none"
    iterations: int = 0
    
    # Fallback and resilience
    fallback_triggered: bool = False
    timeout_protection: bool = False
    retry_count: int = 0
    
    # Performance metrics
    latency_ms_agent_total: int = 0
    latency_ms_tool_execution: int = 0
    
    # Error handling
    failure_reason: Optional[str] = None
    error_class: Optional[str] = None
    safe_degraded_mode: bool = False
    
    # Legacy fields (for backward compatibility)
    mode: Optional[str] = None
    confidence_top: Optional[float] = None
    confidence_threshold: Optional[float] = None
    confidence_decision: Optional[str] = None
    retrieval_pass: str = "none"
    top_k_scores: List[float] = []
    provider: str = "none"
    routing: Optional[str] = None
    tool_used: str = "none"
    latency_ms_total: int = 0
    latency_ms_retrieval: int = 0
    latency_ms_llm: int = 0
    cache_hit: bool = False
    timeout_triggered: bool = False
    
    # RAG Transparency (new semantic fields)
    confidence_path: Optional[str] = None  # high_confidence_direct | low_confidence_hybrid | no_signal_in_document | insufficient_evidence
    answer_status: Optional[str] = None  # confident_answer | uncertain_answer | no_answer_in_document | not_enough_confidence_to_answer
    retrieval_score_primary: Optional[float] = None
    retrieval_score_fallback: Optional[float] = None


class AgentResponse(BaseModel):
    """Response model for agent execution (standard mode)."""
    answer: str
    user_message: str
    meta: Optional[AgentMeta] = None
    trace: List[ToolExecution]
    iterations: int


class VerboseAgentResponse(BaseModel):
    """Response model for agent execution (verbose mode)."""
    answer: str
    user_message: str
    agent_meta: ExtendedAgentMeta
    trace: List[ToolExecution]
    iterations: int


@router.post("/run")
async def run_agent(
    request: AgentRequest,
    verbose: bool = Query(False, description="Include full agent_meta with decision transparency")
):
    """
    Run the AI agent with a natural language prompt.
    
    The agent can intelligently choose between:
    - RAG tool: For answering questions about ingested documents
    - ML tool: For making predictions using the iris classifier
    
    Example prompts:
    - "What does the document say about machine learning?"
    - "Predict the iris species for measurements: 5.1, 3.5, 1.4, 0.2"
    - "Summarize the key findings in the research paper"
    
    Query Parameters:
    - verbose: If true, includes full agent_meta with decision transparency fields
    
    Response includes:
    - answer: The final answer/result
    - user_message: User-friendly explanation of what happened
    - meta/agent_meta: Execution metadata (detailed if verbose=true)
    - trace: Step-by-step execution trace
    - iterations: Number of tool calls made
    """
    with TelemetryTracker(ComponentType.AGENT_RUN) as tracker:
        try:
            logger.info(f"Agent request received: {request.prompt[:100]}... (verbose={verbose})")
            
            # Get agent and run with verbose flag
            agent = get_agent()
            result = agent.run(
                prompt=request.prompt,
                max_iterations=request.max_iterations,
                verbose=verbose
            )
            
            # Set telemetry from agent result
            agent_meta = result.get('agent_meta', result.get('meta', {}))
            if agent_meta:
                # Extract latencies
                if agent_meta.get('latency_ms_total'):
                    tracker.telemetry['latency_ms_total'] = agent_meta['latency_ms_total']
                if agent_meta.get('latency_ms_llm'):
                    tracker.set_llm_latency(agent_meta['latency_ms_llm'])
                if agent_meta.get('latency_ms_retrieval'):
                    tracker.set_retrieval_latency(agent_meta['latency_ms_retrieval'])
                
                # Set confidence and routing
                if agent_meta.get('confidence_top'):
                    tracker.set_confidence(agent_meta['confidence_top'])
                if agent_meta.get('tool_selected'):
                    tracker.set_routing(agent_meta['tool_selected'])
                elif agent_meta.get('tool_used'):
                    tracker.set_routing(agent_meta['tool_used'])
                
                # Check for failures or fallbacks
                if agent_meta.get('fallback_triggered') or agent_meta.get('safe_degraded_mode'):
                    tracker.trigger_fallback(
                        agent_meta.get('failure_reason', 'agent_fallback')
                    )
                    tracker.set_degradation(
                        DegradationLevel.FALLBACK,
                        "Agent used fallback mode",
                        agent_meta.get('failure_reason', 'unknown')
                    )
                
                # Track iterations as retry count
                tracker.telemetry['retry_count'] = result.get('iterations', 0) - 1
            
            logger.info(
                f"Agent completed in {result['iterations']} iterations, "
                f"degradation={tracker.get_telemetry().get('degradation_level')}"
            )
            
            # Return response based on verbose mode
            if verbose and "agent_meta" in result:
                # Merge telemetry into agent_meta
                extended_meta = merge_telemetry(
                    tracker.get_telemetry(),
                    result["agent_meta"]
                )
                return VerboseAgentResponse(
                    answer=result["answer"],
                    user_message=result["user_message"],
                    agent_meta=ExtendedAgentMeta(**extended_meta),
                    trace=[ToolExecution(**t) for t in result["trace"]],
                    iterations=result["iterations"]
                )
            else:
                # Merge telemetry into meta
                meta_data = merge_telemetry(
                    tracker.get_telemetry(),
                    result.get("meta", {})
                )
                return AgentResponse(
                    answer=result["answer"],
                    user_message=result["user_message"],
                    meta=AgentMeta(**meta_data),
                    trace=[ToolExecution(**t) for t in result["trace"]],
                    iterations=result["iterations"]
                )
            
        except ValueError as e:
            logger.error(f"Agent configuration error: {str(e)}")
            tracker.set_degradation(
                DegradationLevel.FAILED,
                "Agent configuration error",
                str(e)
            )
            raise HTTPException(status_code=500, detail=f"Agent configuration error: {str(e)}")
        except Exception as e:
            logger.error(f"Agent execution error: {str(e)}", exc_info=True)
            tracker.set_degradation(
                DegradationLevel.FAILED,
                "Agent execution failed",
                str(e)
            )
            raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")


@router.get("/tools")
async def list_tools():
    """
    List all available tools that the agent can use.
    
    Returns information about each tool's capabilities.
    """
    try:
        agent = get_agent()
        tools_info = []
        
        for tool_name, tool_data in agent.tools.items():
            tools_info.append({
                "name": tool_name,
                "description": tool_data["definition"]["description"],
                "parameters": tool_data["definition"]["parameters"]
            })
        
        return {
            "tools": tools_info,
            "count": len(tools_info)
        }
        
    except Exception as e:
        logger.error(f"Error listing tools: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
