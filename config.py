"""
Configuration settings for the Fact Checker & Response Generator backend.
"""
import os
from dotenv import load_dotenv
from typing import List

# Load environment variables
load_dotenv()

class Settings:
    """Application settings."""
    
    # API settings
    API_TITLE: str = "Fact Checker API"
    API_DESCRIPTION: str = "API for fact-checking and response generation"
    API_VERSION: str = "1.0.0"
    
    # Security settings
    API_KEY_NAME: str = "X-API-Key"
    VALID_API_KEYS: List[str] = []
    
    # OpenAI settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_FACT_CHECK_MODEL: str = os.getenv("OPENAI_FACT_CHECK_MODEL", "gpt-4o")
    OPENAI_RESPONSE_MODEL: str = os.getenv("OPENAI_RESPONSE_MODEL", "gpt-4o-mini")
    
    # Search settings
    SEARCH_API_KEY: str = os.getenv("SEARCH_API_KEY", "")
    SEARCH_API_URL: str = "https://api.bing.microsoft.com/v7.0/search"
    
    # Rate limiting
    RATE_LIMIT_MAX_CALLS: int = 100
    RATE_LIMIT_PERIOD: int = 3600  # 1 hour in seconds
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["chrome-extension://*"]
    
    def __init__(self):
        # Parse API keys from environment variable
        api_keys_env = os.getenv("VALID_API_KEYS", "")
        if api_keys_env:
            try:
                self.VALID_API_KEYS = [key.strip() for key in api_keys_env.split(",") if key.strip()]
                print(f"Loaded {len(self.VALID_API_KEYS)} API keys")
            except Exception as e:
                print(f"Error parsing VALID_API_KEYS: {e}")

# Create settings instance
settings = Settings()

# We'll add a function to add API keys programmatically
def add_api_key(api_key: str):
    """Add an API key to the valid keys list."""
    if api_key and api_key not in settings.VALID_API_KEYS:
        settings.VALID_API_KEYS.append(api_key)
        return True
    return False
