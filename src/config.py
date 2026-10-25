import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base Directory: D:\work\ai-expense-audit-agent
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """Application Settings and Configuration."""
    
    # LLM API Settings
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gemini-3.5-flash-lite"
    
    # Application Mode & Logging
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"
    MOCK_LLM_MODE: bool = False
    
    # Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    OUTPUT_DIR: Path = BASE_DIR / "output"
    
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    def get_masked_api_key(self) -> str:
        """Returns masked API key representation for secure display/logging."""
        key = self.GEMINI_API_KEY or self.OPENAI_API_KEY
        if not key:
            return "NOT_SET"
        if len(key) <= 8:
            return "*****"
        return f"{key[:4]}...{key[-4:]}"

# Singleton settings instance
settings = Settings()

if __name__ == "__main__":
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"LLM Model: {settings.LLM_MODEL}")
    print(f"Mock Mode: {settings.MOCK_LLM_MODE}")
    print(f"API Key Status: {settings.get_masked_api_key()}")
