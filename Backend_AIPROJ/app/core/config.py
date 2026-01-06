import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        self.APP_NAME = os.environ.get("APP_NAME", "FastAPI Application")
        self.ENV = os.environ.get("ENV", "development")
        self.LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
        
        # LLM Provider Configuration
        self.LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "none").lower()
        
        # RAG Safe Mode Configuration
        # STRICT = return no answer when confidence is low
        # HYBRID = call LLM to infer from chunks when confidence is low (default)
        self.RAG_SAFE_MODE = os.environ.get("RAG_SAFE_MODE", "hybrid").lower()
        
        # Cache Configuration
        self.CACHE_ENABLED = os.environ.get("CACHE_ENABLED", "true").lower() == "true"
        self.CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "3600"))
        
        # Resilience Configuration
        self.REQUEST_TIMEOUT_MS = int(os.environ.get("REQUEST_TIMEOUT_MS", "30000"))
        self.MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))
        
        # Confidence Thresholds
        self.CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.55"))
    
    def __repr__(self):
        return (
            f"Settings(APP_NAME={self.APP_NAME}, ENV={self.ENV}, "
            f"LOG_LEVEL={self.LOG_LEVEL}, LLM_PROVIDER={self.LLM_PROVIDER}, "
            f"RAG_SAFE_MODE={self.RAG_SAFE_MODE}, CACHE_ENABLED={self.CACHE_ENABLED})"
        )


settings = Settings()
