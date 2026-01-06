"""
Gemini LLM Provider
Lazy-loaded integration with Google Gemini API.
Only imports dependencies when this provider is selected.
"""

import os
from typing import Dict, Any, Optional, List
from app.core.logging import setup_logger

logger = setup_logger()


class GeminiClient:
    """
    Gemini LLM client with lazy dependency loading.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Google API key (defaults to GEMINI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        # Lazy import - only load when needed
        try:
            from google import genai
            from google.genai import types
            self.genai = genai
            self.types = types
            self.client = genai.Client(api_key=self.api_key)
            logger.info("Gemini client initialized successfully")
        except ImportError as e:
            raise ImportError(
                f"Google GenAI SDK not installed. Install with: pip install google-genai. Error: {e}"
            )
    
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        model: str = "gemini-2.5-flash-lite"
    ) -> Dict[str, Any]:
        """
        Generate a response using Gemini.
        
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
            # Build config
            config_args = {"temperature": temperature}
            
            if system:
                config_args["system_instruction"] = system
            
            # Convert tools to Gemini format if provided
            if tools:
                tool_declarations = [
                    self.types.Tool(
                        function_declarations=[
                            self.types.FunctionDeclaration(
                                name=tool["name"],
                                description=tool["description"],
                                parameters=tool["parameters"]
                            )
                            for tool in tools
                        ]
                    )
                ]
                config_args["tools"] = tool_declarations
                config_args["tool_config"] = self.types.ToolConfig(
                    function_calling_config=self.types.FunctionCallingConfig(mode="AUTO")
                )
            
            config = self.types.GenerateContentConfig(**config_args)
            
            # Generate response
            response = self.client.models.generate_content(
                model=model,
                contents=prompt,
                config=config
            )
            
            # Extract text
            text = ""
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text') and part.text:
                        text += part.text
            
            logger.info("Gemini generation successful")
            
            return {
                "text": text,
                "provider": "gemini",
                "raw": response
            }
            
        except Exception as e:
            logger.error(f"Gemini generation failed: {str(e)}")
            raise


def call_gemini(
    prompt: str,
    system: Optional[str] = None,
    tools: Optional[List[Dict]] = None,
    temperature: float = 0.7
) -> Dict[str, Any]:
    """
    Convenience function to call Gemini.
    
    Args:
        prompt: User prompt
        system: System instruction
        tools: Tool definitions
        temperature: Sampling temperature
        
    Returns:
        Dict with response
    """
    client = GeminiClient()
    return client.generate(prompt, system, tools, temperature)
