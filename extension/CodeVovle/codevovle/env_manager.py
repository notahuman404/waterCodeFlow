"""
Environment variable management for CodeVovle.

Loads API keys from .env file in project root.
Supports multiple AI models: Gemini (default), ChatGPT, Claude.
"""

import os
from pathlib import Path
from typing import Optional


class EnvManager:
    """Manages environment variables and API keys."""
    
    _keys = None
    
    @classmethod
    def _load_env(cls):
        """Load .env file if not already loaded."""
        if cls._keys is not None:
            return
        
        cls._keys = {}
        env_path = Path.cwd() / ".env"
        
        if not env_path.exists():
            return
        
        try:
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        cls._keys[key.strip()] = value.strip()
        except Exception:
            pass
    
    @classmethod
    def get_api_key(cls, model: str) -> Optional[str]:
        """
        Get API key for a model.
        
        Args:
            model: Model name ('gemini', 'chatgpt', 'claude')
            
        Returns:
            API key or None if not found/empty
        """
        cls._load_env()
        
        model_lower = model.lower()
        # Check .env keys first (lowercase keys stored), then common env var names
        key = None
        if cls._keys:
            key = cls._keys.get(model_lower)

        if not key:
            # Try plain uppercase model name (e.g., CLAUDE)
            key = os.environ.get(model_lower.upper())

        if not key:
            # Try common API key suffix (e.g., CLAUDE_API_KEY)
            key = os.environ.get(f"{model_lower.upper()}_API_KEY")
        
        # Return None if key is "None" string or empty
        if key and key.lower() != "none" and key.strip():
            return key
        return None
    
    @classmethod
    def has_api_key(cls, model: str) -> bool:
        """Check if API key exists for a model."""
        return cls.get_api_key(model) is not None
    
    @classmethod
    def get_available_models(cls) -> list[str]:
        """Get list of available AI models with valid API keys."""
        models = ['gemini', 'chatgpt', 'claude']
        return [m for m in models if cls.has_api_key(m)]
