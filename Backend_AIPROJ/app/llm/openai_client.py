"""
OpenAI LLM Provider
Lazy-loaded integration with OpenAI API.
Only imports dependencies when this provider is selected.
"""

import os
from typing import Dict, Any, Optional, List
from app.core.logging import setup_logger

logger = setup_logger()


class OpenAIClient:
    """
    OpenAI LLM client with lazy dependency loading.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        # Lazy import - only load when needed
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
            logger.info("OpenAI client initialized successfully")
        except ImportError as e:
            raise ImportError(
                f"OpenAI SDK not installed. Install with: pip install openai. Error: {e}"
            )
    
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        model: str = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        """
        Generate a response using OpenAI.
        
        Args:
            prompt: User prompt
            system: System instruction (optional)
            tools: List of tool definitions (optional)
            temperature: Sampling temperature
            model: Model name
            
        Returns:
            Dict with 'text', 'provider', 'raw' keys
        """
        try:
            # Build messages
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            
            # Build request args
            request_args = {
                "model": model,
                "messages": messages,
                "temperature": temperature
            }
            
            # Add tools if provided
            if tools:
                openai_tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool["description"],
                            "parameters": tool["parameters"]
                        }
                    }
                    for tool in tools
                ]
                request_args["tools"] = openai_tools
                request_args["tool_choice"] = "auto"
            
            # Try primary model first, fallback to gpt-3.5-turbo if fails
            try:
                response = self.client.chat.completions.create(**request_args)
            except Exception as e:
                if model == "gpt-4o-mini":
                    logger.warning(f"gpt-4o-mini failed, falling back to gpt-3.5-turbo: {e}")
                    request_args["model"] = "gpt-3.5-turbo"
                    response = self.client.chat.completions.create(**request_args)
                else:
                    raise
            
            # Extract text
            text = response.choices[0].message.content or ""
            
            logger.info(f"OpenAI generation successful (model: {request_args['model']})")
            
            return {
                "text": text,
                "provider": "openai",
                "raw": response
            }
            
        except Exception as e:
            logger.error(f"OpenAI generation failed: {str(e)}")
            raise


def call_openai(
    prompt: str,
    system: Optional[str] = None,
    tools: Optional[List[Dict]] = None,
    temperature: float = 0.7
) -> Dict[str, Any]:
    """
    Convenience function to call OpenAI.
    
    Args:
        prompt: User prompt
        system: System instruction
        tools: Tool definitions
        temperature: Sampling temperature
        
    Returns:
        Dict with response
    """
    client = OpenAIClient()
    return client.generate(prompt, system, tools, temperature)
