"""
LLM Router
Central routing logic for selecting and calling LLM providers.
Supports fallback chains and graceful degradation.
"""

import os
from typing import Dict, Any, Optional, List
from app.core.logging import setup_logger

logger = setup_logger()


def is_llm_configured() -> bool:
    """
    Check if any LLM provider is properly configured.
    
    Returns:
        True if at least one LLM provider has API key configured
    """
    provider = get_provider()
    
    if provider == "none":
        return False
    
    if provider == "gemini" or provider == "auto":
        if os.getenv("GEMINI_API_KEY"):
            return True
    
    if provider == "openai" or provider == "auto":
        if os.getenv("OPENAI_API_KEY"):
            return True
    
    if provider == "ollama":
        return True  # Ollama runs locally
    
    return False


def get_provider() -> str:
    """
    Get the configured LLM provider from environment.
    
    Returns:
        Provider name: 'none', 'gemini', 'openai', 'ollama', or 'auto'
    """
    return os.getenv("LLM_PROVIDER", "none").lower()


def call_llm(
    prompt: str,
    system: Optional[str] = None,
    tools: Optional[List[Dict]] = None,
    mode: str = "chat",
    temperature: float = 0.7
) -> Dict[str, Any]:
    """
    Routes the request to the active LLM provider with fallback logic.
    
    Provider priority:
    1) Provider selected in LLM_PROVIDER config
    2) 'auto' mode: try Gemini → OpenAI → Ollama
    3) 'none': return friendly message
    
    Args:
        prompt: User prompt
        system: System instruction (optional)
        tools: List of tool definitions (optional)
        mode: Mode of operation ('chat', 'completion', etc.)
        temperature: Sampling temperature
        
    Returns:
        Unified response format:
        {
            "text": str,           # Generated text
            "provider": str,       # Provider used
            "raw": object          # Raw response object
        }
        
    Raises:
        Exception: If all providers fail or none configured
    """
    provider = get_provider()
    
    # Handle 'none' provider - lightweight mode
    if provider == "none":
        logger.info("LLM provider not enabled - running in lightweight mode")
        return {
            "text": "LLM provider not enabled — running in lightweight mode. To enable, set LLM_PROVIDER environment variable to 'gemini', 'openai', 'ollama', or 'auto'.",
            "provider": "none",
            "raw": None
        }
    
    # Handle specific provider
    if provider in ["gemini", "openai", "ollama"]:
        return _call_specific_provider(provider, prompt, system, tools, temperature)
    
    # Handle 'auto' mode - try all providers in order
    if provider == "auto":
        return _call_with_fallback(prompt, system, tools, temperature)
    
    # Unknown provider
    logger.warning(f"Unknown LLM_PROVIDER: {provider}, falling back to 'none'")
    return {
        "text": f"Unknown LLM provider '{provider}'. Set LLM_PROVIDER to 'none', 'gemini', 'openai', 'ollama', or 'auto'.",
        "provider": "none",
        "raw": None
    }


def _call_specific_provider(
    provider: str,
    prompt: str,
    system: Optional[str],
    tools: Optional[List[Dict]],
    temperature: float
) -> Dict[str, Any]:
    """
    Call a specific LLM provider.
    
    Args:
        provider: Provider name ('gemini', 'openai', 'ollama')
        prompt: User prompt
        system: System instruction
        tools: Tool definitions
        temperature: Sampling temperature
        
    Returns:
        Response dict
        
    Raises:
        Exception: If provider fails
    """
    try:
        if provider == "gemini":
            from app.llm.gemini_client import call_gemini
            logger.info("Using Gemini provider")
            return call_gemini(prompt, system, tools, temperature)
        
        elif provider == "openai":
            from app.llm.openai_client import call_openai
            logger.info("Using OpenAI provider")
            return call_openai(prompt, system, tools, temperature)
        
        elif provider == "ollama":
            from app.llm.ollama_client import call_ollama
            logger.info("Using Ollama provider")
            return call_ollama(prompt, system, tools, temperature)
    
    except ImportError as e:
        error_msg = f"{provider.capitalize()} provider not available: {str(e)}"
        logger.error(error_msg)
        return None
    
    except ValueError as e:
        # Missing API key
        error_msg = f"{provider.capitalize()} provider not configured: {str(e)}"
        logger.error(error_msg)
        return None
    
    except Exception as e:
        error_msg = f"{provider.capitalize()} provider failed: {str(e)}"
        logger.error(error_msg)
        return None


def _call_with_fallback(
    prompt: str,
    system: Optional[str],
    tools: Optional[List[Dict]],
    temperature: float
) -> Dict[str, Any]:
    """
    Try multiple providers with fallback logic.
    Order: Gemini → OpenAI → Ollama
    
    Args:
        prompt: User prompt
        system: System instruction
        tools: Tool definitions
        temperature: Sampling temperature
        
    Returns:
        Response from first successful provider, or safe fallback response
    """
    providers = ["gemini", "openai", "ollama"]
    
    for provider in providers:
        logger.info(f"Attempting provider: {provider}")
        result = _call_specific_provider(provider, prompt, system, tools, temperature)
        if result is not None:
            return result
        logger.warning(f"Provider {provider} failed, trying next provider")
    
    # All providers failed - return safe response
    logger.error("All LLM providers failed - returning lightweight mode response")
    return {
        "text": "No LLM provider is currently available. The system is running in lightweight mode. Enable Gemini, OpenAI, or Ollama in the configuration.",
        "provider": "none",
        "raw": None
    }


def is_llm_enabled() -> bool:
    """
    Check if any LLM provider is enabled.
    
    Returns:
        bool: True if LLM is enabled, False if 'none'
    """
    provider = get_provider()
    return provider != "none"
