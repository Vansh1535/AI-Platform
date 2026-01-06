"""
Ollama LLM Provider
Lazy-loaded integration with Ollama local models.
Only imports dependencies when this provider is selected.
"""

import os
from typing import Dict, Any, Optional, List
from app.core.logging import setup_logger

logger = setup_logger()


class OllamaClient:
    """
    Ollama LLM client with lazy dependency loading.
    """
    
    def __init__(self, host: Optional[str] = None):
        """
        Initialize Ollama client.
        
        Args:
            host: Ollama server URL (defaults to OLLAMA_HOST env var or http://localhost:11434)
        """
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        
        # Lazy import - only load when needed
        try:
            import ollama
            self.ollama = ollama
            logger.info(f"Ollama client initialized (host: {self.host})")
        except ImportError as e:
            raise ImportError(
                f"Ollama SDK not installed. Install with: pip install ollama. Error: {e}"
            )
    
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        model: str = "llama3.2"
    ) -> Dict[str, Any]:
        """
        Generate a response using Ollama.
        
        Args:
            prompt: User prompt
            system: System instruction (optional)
            tools: List of tool definitions (optional - not fully supported yet)
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
            
            # Generate response
            # Note: Ollama's tool/function calling support varies by model
            response = self.ollama.chat(
                model=model,
                messages=messages,
                options={
                    "temperature": temperature
                }
            )
            
            # Extract text
            text = response.get("message", {}).get("content", "")
            
            logger.info(f"Ollama generation successful (model: {model})")
            
            return {
                "text": text,
                "provider": "ollama",
                "raw": response
            }
            
        except Exception as e:
            logger.error(f"Ollama generation failed: {str(e)}")
            raise


def call_ollama(
    prompt: str,
    system: Optional[str] = None,
    tools: Optional[List[Dict]] = None,
    temperature: float = 0.7
) -> Dict[str, Any]:
    """
    Convenience function to call Ollama.
    
    Args:
        prompt: User prompt
        system: System instruction
        tools: Tool definitions (limited support)
        temperature: Sampling temperature
        
    Returns:
        Dict with response
    """
    client = OllamaClient()
    return client.generate(prompt, system, tools, temperature)
