"""
LLM Provider Module
Modular, optional LLM integrations for Gemini, OpenAI, and Ollama.
"""

from app.llm.router import call_llm

__all__ = ["call_llm"]
