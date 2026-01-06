"""
Updated simple_agent.py with decision transparency and user-facing messages.
Extensions added: agent_meta fields, user_message, verbose mode support.
No changes to execution logic - only instrumentation added.
"""

import os
import json
import time
from typing import Dict, Any, Optional
from app.core.logging import setup_logger
from app.llm.router import call_llm, is_llm_enabled
from app.agents.tools.rag_tool import ask_document, get_rag_tool_definition
from app.agents.tools.ml_tool import predict_ml, get_ml_tool_definition

logger = setup_logger()

# Explicit document reference signals
EXPLICIT_DOCUMENT_SIGNALS = [
    "document", "pdf", "resume", "file", "content", "text",
    "from doc", "in the document", "in this file", "in the doc",
    "according to", "in the resume", "from the file", "in the pdf",
    "document says", "file contains", "resume shows", "cv shows",
    "in this resume", "from this document", "based on the document"
]

# Semantic patterns that suggest document queries (when combined with context)
SEMANTIC_DOCUMENT_PATTERNS = [
    "name", "role", "title", "position", "job", "details", 
    "information", "summary", "experience", "education",
    "skills", "background", "contact", "email", "phone",
    "address", "company", "project", "qualification",
    "certification", "degree", "university", "achievement"
]

# Negative signals indicating general/reasoning questions
GENERAL_QUERY_SIGNALS = [
    "what is", "how to", "why", "explain", "calculate", "compute",
    "what does", "how does", "tell me about", "describe how",
    "2+2", "math", "formula", "equation", "prove", "solve",
    "difference between", "compare", "versus", "vs", "or"
]


def classify_intent(prompt: str) -> str:
    """
    Classify if a prompt is document-related or general using context-aware heuristics.
    
    Strategy:
    1. Check for explicit document references (high confidence)
    2. Check for general/reasoning question patterns (negative signals)
    3. Check for semantic patterns that might indicate document queries
    4. Default to general to avoid false positives
    
    Args:
        prompt: The user's prompt
    
    Returns:
        str: "document_query" if document-related, "general_query" otherwise
    """
    prompt_lower = prompt.lower()
    
    # Step 1: Check for explicit document signals (highest priority)
    for signal in EXPLICIT_DOCUMENT_SIGNALS:
        if signal in prompt_lower:
            logger.info(f"intent=document_query - Explicit signal matched: '{signal}'")
            return "document_query"
    
    # Step 2: Check for general/reasoning question patterns (negative signals)
    for signal in GENERAL_QUERY_SIGNALS:
        if signal in prompt_lower:
            logger.info(f"intent=general_query - General signal matched: '{signal}'")
            return "general_query"
    
    # Step 3: Check for semantic patterns (lower confidence, requires caution)
    # Only classify as document query if semantic pattern is strong
    semantic_matches = []
    for pattern in SEMANTIC_DOCUMENT_PATTERNS:
        if pattern in prompt_lower:
            semantic_matches.append(pattern)
    
    # If multiple semantic patterns match, it's likely a document query
    # But we need at least 2 matches to avoid false positives
    if len(semantic_matches) >= 2:
        logger.info(f"intent=document_query - Multiple semantic patterns matched: {semantic_matches[:3]}")
        return "document_query"
    
    # Step 4: Check for "who is" + semantic pattern (common document query)
    if "who is" in prompt_lower and semantic_matches:
        logger.info(f"intent=document_query - 'who is' + semantic pattern: {semantic_matches[0]}")
        return "document_query"
    
    # Step 5: Default to general query to avoid false positives
    logger.info(f"intent=general_query - No strong document signals detected")
    return "general_query"


class SimpleAgent:
    """
    An AI agent that can intelligently choose between RAG and ML tools.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the agent with LLM router and tools.
        
        Args:
            api_key: Deprecated - LLM provider configured via LLM_PROVIDER env var
        """
        # Check if LLM is enabled
        if not is_llm_enabled():
            logger.warning("Agent initialized but LLM provider is disabled. Set LLM_PROVIDER to use agent.")
        
        # Register tools
        self.tools = {
            "ask_document": {
                "function": ask_document,
                "definition": get_rag_tool_definition()
            },
            "predict_ml": {
                "function": predict_ml,
                "definition": get_ml_tool_definition()
            }
        }
        
        logger.info(f"Agent initialized with {len(self.tools)} tools")
    
    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> tuple[str, Dict]:
        """
        Execute a tool with given arguments.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Dictionary of arguments for the tool
            
        Returns:
            Tuple of (result_str, telemetry_dict): Result from tool execution and metadata
        """
        if tool_name not in self.tools:
            return f"Error: Unknown tool '{tool_name}'", {"error_class": "UNKNOWN_TOOL"}
        
        # Normalize arguments for predict_ml tool
        if tool_name == "predict_ml":
            arguments = self._normalize_ml_arguments(arguments)
            if isinstance(arguments, str):  # Error message returned
                return arguments, {"error_class": "INVALID_ARGUMENTS"}
        
        try:
            tool_func = self.tools[tool_name]["function"]
            result = tool_func(**arguments)
            
            # Check if result is tuple (new telemetry format)
            if isinstance(result, tuple) and len(result) == 2:
                result_str, telemetry = result
                logger.info(f"Tool '{tool_name}' executed successfully with telemetry")
                return result_str, telemetry
            else:
                # Old format (backward compatibility)
                logger.info(f"Tool '{tool_name}' executed successfully (no telemetry)")
                return result, {}
        except Exception as e:
            error_msg = f"Error executing tool '{tool_name}': {str(e)}"
            logger.error(error_msg)
            return error_msg, {"error_class": "TOOL_EXECUTION_ERROR"}
    
    def _normalize_ml_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any] | str:
        """
        Normalize ML tool arguments to handle both array and named parameter formats.
        
        Format A (array): {"features": [5.1, 3.5, 1.4, 0.2]}
        Format B (named): {"sepal_length": 5.1, "sepal_width": 3.5, ...}
        
        Args:
            arguments: Raw arguments from LLM
            
        Returns:
            Normalized arguments dict, or error string if invalid
        """
        # If features array already present, prefer it
        if "features" in arguments:
            features = arguments["features"]
            # Validate
            if not isinstance(features, list) or len(features) != 4:
                return "Invalid ML input: expected 4 numeric features"
            if not all(isinstance(f, (int, float)) for f in features):
                return "Invalid ML input: expected 4 numeric features"
            return arguments
        
        # Check if named parameters are present
        named_params = ["sepal_length", "sepal_width", "petal_length", "petal_width"]
        if all(param in arguments for param in named_params):
            # Extract values in correct order
            try:
                features = [
                    float(arguments["sepal_length"]),
                    float(arguments["sepal_width"]),
                    float(arguments["petal_length"]),
                    float(arguments["petal_width"])
                ]
                logger.info(f"normalized_ml_arguments=true - Converted named params to array: {features}")
                return {"features": features}
            except (ValueError, TypeError) as e:
                return f"Invalid ML input: expected 4 numeric features, got conversion error: {str(e)}"
        
        # Neither format present
        return "Invalid ML input: expected either 'features' array or named parameters (sepal_length, sepal_width, petal_length, petal_width)"
    
    def run(self, prompt: str, max_iterations: int = 5, verbose: bool = False) -> Dict[str, Any]:
        """
        Run the agent with a user prompt.
        
        Args:
            prompt: User's natural language prompt
            max_iterations: Maximum number of tool calls (default: 5)
            verbose: If True, include full agent_meta in response (default: False)
            
        Returns:
            dict: Response with answer, user_message, agent_meta (if verbose), trace, and iterations
        """
        # Capture start time for latency tracking
        start_time = time.time()
        tool_start_time = None
        
        # Initialize extended agent metadata with all transparency fields
        agent_meta = {
            # Decision routing
            "decision_route": None,
            "reason": None,
            "tool_selected": None,
            "tool_confidence": None,
            "alternatives_considered": [],
            
            # Provider and execution
            "provider_used": "none",
            "iterations": 0,
            
            # Fallback and resilience
            "fallback_triggered": False,
            "timeout_protection": False,
            "retry_count": 0,
            
            # Performance metrics
            "latency_ms_agent_total": 0,
            "latency_ms_tool_execution": 0,
            
            # Error handling
            "failure_reason": None,
            "error_class": None,
            "safe_degraded_mode": False,
            
            # Legacy fields (for backward compatibility)
            "mode": None,
            "confidence_top": None,
            "confidence_threshold": None,
            "confidence_decision": None,
            "retrieval_pass": "none",
            "top_k_scores": [],
            "provider": "none",
            "routing": None,
            "tool_used": "none",
            "latency_ms_total": 0,
            "latency_ms_retrieval": 0,
            "latency_ms_llm": 0,
            "cache_hit": False,
            "timeout_triggered": False
        }
        
        # User-facing message (graceful explanation)
        user_message = ""
        
        logger.info(f"Agent running with prompt: {prompt[:100]}...")
        
        # Classify intent before any LLM call
        intent = classify_intent(prompt)
        
        # If document-related, force RAG tool immediately
        if intent == "document_query":
            logger.info("routing=force_rag_tool - Document query detected, calling ask_document directly")
            
            # Update agent metadata for decision transparency
            agent_meta["decision_route"] = "force_rag_document"
            agent_meta["reason"] = "Document-related query detected via intent classification"
            agent_meta["tool_selected"] = "ask_document"
            agent_meta["tool_confidence"] = 0.95
            agent_meta["alternatives_considered"] = ["llm_direct", "ask_document"]
            
            # Legacy fields
            agent_meta["routing"] = "force_rag_tool"
            agent_meta["tool_used"] = "ask_document"
            agent_meta["mode"] = "rag_direct"
            
            logger.info(f"decision_transparency - route={agent_meta['decision_route']} tool={agent_meta['tool_selected']} confidence={agent_meta['tool_confidence']}")
            
            execution_trace = []
            try:
                # Track tool execution time
                tool_start_time = time.time()
                
                # Execute ask_document tool directly - now returns tuple with telemetry
                tool_result, tool_telemetry = self._execute_tool("ask_document", {"question": prompt})
                
                # Calculate tool execution latency
                tool_latency = int((time.time() - tool_start_time) * 1000)
                agent_meta["latency_ms_tool_execution"] = tool_latency
                
                # Merge tool telemetry into agent_meta
                agent_meta.update(tool_telemetry)
                
                # Determine user message based on RAG confidence and mode
                mode = tool_telemetry.get("mode", "unknown")
                confidence = tool_telemetry.get("confidence_top", 0)
                
                if mode == "rag_confident":
                    user_message = "Answer generated successfully from document content."
                    logger.info("user_message=success_confident - High confidence RAG answer")
                elif mode == "rag_llm_hybrid":
                    user_message = f"Document evidence found (confidence: {confidence:.2f}), enhanced with reasoning."
                    logger.info("user_message=success_hybrid - Low confidence, used LLM enhancement")
                elif mode == "safe_fallback":
                    user_message = "Unable to find relevant information in the document. Providing safe response."
                    logger.info("user_message=no_content - Document does not contain requested information")
                elif "no document" in tool_result.lower() or "not found" in tool_result.lower():
                    user_message = "The document does not contain information related to your question."
                    logger.info("user_message=not_found - No relevant document content")
                else:
                    user_message = "Answer generated successfully."
                    logger.info("user_message=success_default - RAG answer completed")
                
                execution_trace.append({
                    "iteration": 1,
                    "tool": "ask_document",
                    "arguments": {"question": prompt},
                    "result": tool_result,
                    "routing": "force_rag_tool",
                    "telemetry": tool_telemetry
                })
                
                # Calculate total latency
                total_latency = int((time.time() - start_time) * 1000)
                agent_meta["latency_ms_agent_total"] = total_latency
                agent_meta["latency_ms_total"] = total_latency  # Legacy
                agent_meta["iterations"] = 1
                agent_meta["provider_used"] = agent_meta.get("provider", "none")
                
                logger.info(f"Agent completed via forced RAG routing mode={agent_meta.get('mode')} cache_hit={agent_meta.get('cache_hit')}")
                logger.info(f"decision_transparency - latency={total_latency}ms tool_latency={tool_latency}ms")
                logger.info("meta_generated=true")
                
                response = {
                    "answer": tool_result,
                    "user_message": user_message,
                    "trace": execution_trace,
                    "iterations": 1
                }
                
                # Include agent_meta only if verbose mode
                if verbose:
                    response["agent_meta"] = agent_meta
                    logger.info("verbose_mode=true - Including full agent_meta")
                else:
                    # Minimal meta for backward compatibility
                    response["meta"] = {
                        "mode": agent_meta.get("mode"),
                        "provider": agent_meta.get("provider"),
                        "tool_used": agent_meta.get("tool_used"),
                        "latency_ms_total": agent_meta.get("latency_ms_total")
                    }
                
                return response
                
            except Exception as e:
                error_msg = f"RAG tool error: {str(e)}"
                logger.error(error_msg)
                logger.error(f"error_transparency - class=TOOL_EXECUTION_ERROR reason={str(e)}")
                
                # Calculate total latency
                total_latency = int((time.time() - start_time) * 1000)
                agent_meta["latency_ms_agent_total"] = total_latency
                agent_meta["latency_ms_total"] = total_latency
                agent_meta["error_class"] = "TOOL_EXECUTION_ERROR"
                agent_meta["failure_reason"] = str(e)
                agent_meta["iterations"] = 1
                
                # Graceful user message for tool failure
                user_message = "Primary document search tool failed. Please try rephrasing your question."
                if "timeout" in str(e).lower():
                    user_message = "Document search timed out. Please try again or simplify your query."
                    agent_meta["timeout_protection"] = True
                
                logger.info(f"user_message=tool_error - {user_message}")
                logger.info("meta_generated=true")
                
                response = {
                    "answer": error_msg,
                    "user_message": user_message,
                    "trace": execution_trace,
                    "iterations": 1
                }
                
                if verbose:
                    response["agent_meta"] = agent_meta
                else:
                    response["meta"] = {
                        "error_class": agent_meta.get("error_class"),
                        "latency_ms_total": agent_meta.get("latency_ms_total")
                    }
                
                return response
        
        # Non-document query: use LLM reasoning
        logger.info("routing=llm_direct - Non-document query, allowing LLM reasoning")
        
        # Update agent metadata for decision transparency
        agent_meta["decision_route"] = "llm_reasoning"
        agent_meta["reason"] = "General query without document reference"
        agent_meta["tool_selected"] = "llm_direct"
        agent_meta["alternatives_considered"] = ["ask_document", "llm_direct"]
        agent_meta["mode"] = "llm_direct"
        agent_meta["routing"] = "llm_direct"
        
        logger.info(f"decision_transparency - route={agent_meta['decision_route']} reason={agent_meta['reason']}")
        
        # Check if LLM is enabled
        if not is_llm_enabled():
            logger.warning("Agent requires LLM provider - currently disabled")
            logger.warning("fallback_transparency - LLM unavailable, entering safe degraded mode")
            
            # Calculate total latency
            total_latency = int((time.time() - start_time) * 1000)
            agent_meta["latency_ms_agent_total"] = total_latency
            agent_meta["latency_ms_total"] = total_latency
            agent_meta["error_class"] = "LLM_PROVIDER_UNAVAILABLE"
            agent_meta["failure_reason"] = "LLM provider not configured or unavailable"
            agent_meta["safe_degraded_mode"] = True
            agent_meta["iterations"] = 0
            
            # Graceful user message for offline mode
            user_message = "LLM unavailable — continuing in safe offline mode. Please configure LLM_PROVIDER for enhanced responses."
            
            logger.info(f"user_message=llm_offline - {user_message}")
            logger.info("meta_generated=true")
            
            response = {
                "answer": "Agent functionality requires an LLM provider. Please set LLM_PROVIDER environment variable to 'gemini', 'openai', 'ollama', or 'auto'.",
                "user_message": user_message,
                "trace": [],
                "iterations": 0
            }
            
            if verbose:
                response["agent_meta"] = agent_meta
            else:
                response["meta"] = {
                    "error_class": agent_meta.get("error_class"),
                    "safe_degraded_mode": True,
                    "latency_ms_total": agent_meta.get("latency_ms_total")
                }
            
            return response
        
        # Prepare tool definitions in unified format
        tool_definitions = [
            tool_def["definition"]
            for tool_def in self.tools.values()
        ]
        
        # System instruction for non-document queries
        system_instruction = """You are a helpful AI assistant with access to specialized tools.

Available tools:
- predict_ml: For iris flower classification with 4 numerical features (sepal_length, sepal_width, petal_length, petal_width)

For iris predictions, respond with the predicted class based on the features provided.
For general questions not requiring tools, provide helpful direct responses."""
        
        execution_trace = []
        
        try:
            # Track LLM call time
            llm_start_time = time.time()
            
            # Call LLM with tools using unified router
            logger.info("Calling LLM via router for non-document query")
            logger.info("execution_transparency - calling LLM with tool definitions")
            
            llm_response = call_llm(
                prompt=prompt,
                system=system_instruction,
                tools=tool_definitions,
                temperature=0.7
            )
            
            # Calculate LLM latency
            llm_latency = int((time.time() - llm_start_time) * 1000)
            agent_meta["latency_ms_llm"] = llm_latency
            
            answer_text = llm_response["text"]
            provider = llm_response["provider"]
            
            # Update metadata with provider
            agent_meta["provider"] = provider
            agent_meta["provider_used"] = provider
            
            logger.info(f"provider_transparency - provider={provider} latency={llm_latency}ms")
            
            # Check if ML prediction is needed
            if "iris" in prompt.lower() or "predict" in prompt.lower():
                # Check if features are provided
                import re
                numbers = re.findall(r'\d+\.?\d*', prompt)
                if len(numbers) >= 4:
                    try:
                        features = [float(n) for n in numbers[:4]]
                        logger.info("Executing predict_ml tool based on detected features")
                        logger.info(f"tool_transparency - switching to predict_ml tool with features={features}")
                        
                        # Track tool execution time
                        tool_start_time = time.time()
                        
                        # Update metadata for ML tool usage
                        agent_meta["tool_used"] = "predict_ml"
                        agent_meta["tool_selected"] = "predict_ml"
                        agent_meta["mode"] = "tool_chain"
                        agent_meta["decision_route"] = "llm_with_tool"
                        agent_meta["reason"] = "ML prediction detected with numeric features"
                        
                        tool_result, tool_telemetry = self._execute_tool("predict_ml", {
                            "sepal_length": features[0],
                            "sepal_width": features[1],
                            "petal_length": features[2],
                            "petal_width": features[3]
                        })
                        
                        # Calculate tool execution latency
                        tool_latency = int((time.time() - tool_start_time) * 1000)
                        agent_meta["latency_ms_tool_execution"] = tool_latency
                        
                        # Merge tool telemetry
                        agent_meta.update(tool_telemetry)
                        
                        logger.info(f"tool_transparency - predict_ml completed in {tool_latency}ms")
                        
                        execution_trace.append({
                            "iteration": 1,
                            "tool": "predict_ml",
                            "arguments": {
                                "sepal_length": features[0],
                                "sepal_width": features[1],
                                "petal_length": features[2],
                                "petal_width": features[3]
                            },
                            "result": tool_result,
                            "routing": "llm_direct",
                            "telemetry": tool_telemetry
                        })
                        answer_text = tool_result
                        user_message = "ML prediction completed successfully using iris classifier."
                        logger.info("user_message=ml_success - Prediction generated")
                    except Exception as e:
                        logger.warning(f"Failed to parse ML features: {e}")
                        logger.warning(f"fallback_transparency - ML tool failed, falling back to LLM response")
                        agent_meta["error_class"] = "FEATURE_PARSING_ERROR"
                        agent_meta["fallback_triggered"] = True
                        agent_meta["failure_reason"] = f"ML feature parsing failed: {str(e)}"
                        user_message = "Primary ML tool failed, using alternative reasoning path."
                        logger.info("user_message=ml_fallback - Using LLM fallback")
            
            # Set default user message if not already set
            if not user_message:
                user_message = "Answer generated successfully."
                logger.info("user_message=llm_success - Direct LLM response")
            
            # Calculate total latency
            total_latency = int((time.time() - start_time) * 1000)
            agent_meta["latency_ms_agent_total"] = total_latency
            agent_meta["latency_ms_total"] = total_latency
            agent_meta["iterations"] = 1
            
            logger.info(f"Agent completed via LLM direct routing provider={provider} mode={agent_meta.get('mode')}")
            logger.info(f"performance_transparency - total={total_latency}ms llm={llm_latency}ms")
            logger.info("meta_generated=true")
            
            response = {
                "answer": answer_text,
                "user_message": user_message,
                "trace": execution_trace,
                "iterations": 1
            }
            
            if verbose:
                response["agent_meta"] = agent_meta
                logger.info("verbose_mode=true - Including full agent_meta")
            else:
                # Minimal meta for backward compatibility
                response["meta"] = {
                    "mode": agent_meta.get("mode"),
                    "provider": agent_meta.get("provider"),
                    "tool_used": agent_meta.get("tool_used"),
                    "latency_ms_total": agent_meta.get("latency_ms_total")
                }
            
            return response
            
        except Exception as e:
            error_msg = f"Agent error: {str(e)}"
            logger.error(error_msg)
            logger.error(f"error_transparency - class=AGENT_EXECUTION_ERROR reason={str(e)}")
            
            # Calculate total latency
            total_latency = int((time.time() - start_time) * 1000)
            agent_meta["latency_ms_agent_total"] = total_latency
            agent_meta["latency_ms_total"] = total_latency
            agent_meta["error_class"] = "AGENT_EXECUTION_ERROR"
            agent_meta["failure_reason"] = str(e)
            agent_meta["iterations"] = 1
            agent_meta["safe_degraded_mode"] = True
            
            # Graceful user message for general errors
            user_message = "An unexpected error occurred. Please try rephrasing your request."
            if "timeout" in str(e).lower():
                user_message = "Request timed out. Please try again with a simpler query."
                agent_meta["timeout_protection"] = True
            elif "rate limit" in str(e).lower():
                user_message = "Service temporarily unavailable due to high demand. Please try again shortly."
            
            logger.info(f"user_message=agent_error - {user_message}")
            logger.info("meta_generated=true")
            
            response = {
                "answer": f"Error: {str(e)}",
                "user_message": user_message,
                "trace": execution_trace,
                "iterations": 1
            }
            
            if verbose:
                response["agent_meta"] = agent_meta
            else:
                response["meta"] = {
                    "error_class": agent_meta.get("error_class"),
                    "safe_degraded_mode": True,
                    "latency_ms_total": agent_meta.get("latency_ms_total")
                }
            
            return response


# Singleton instance
_agent_instance: Optional[SimpleAgent] = None


def get_agent() -> SimpleAgent:
    """
    Get or create the singleton agent instance.
    
    Returns:
        SimpleAgent: The agent instance
    """
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = SimpleAgent()
    return _agent_instance
