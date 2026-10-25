import pytest
from pathlib import Path
from src.config import Settings

@pytest.fixture
def mock_settings(tmp_path: Path) -> Settings:
    """Fixture returning temporary test settings instance."""
    return Settings(
        ENVIRONMENT="testing",
        LOG_LEVEL="DEBUG",
        MOCK_LLM_MODE=True,
        BASE_DIR=tmp_path,
        DATA_DIR=tmp_path / "data",
        OUTPUT_DIR=tmp_path / "output"
    )
