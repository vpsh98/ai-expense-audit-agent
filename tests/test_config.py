from src.config import settings, Settings
from src.utils.logger import get_logger

def test_default_settings():
    """Verify default settings load cleanly without errors."""
    assert settings.ENVIRONMENT in ["development", "testing", "production"]
    assert isinstance(settings.LLM_MODEL, str)
    assert settings.BASE_DIR.exists()

def test_masked_api_key():
    """Verify API keys are masked appropriately for display."""
    test_set = Settings(GEMINI_API_KEY="AIzaSy1234567890SecretKey")
    assert test_set.get_masked_api_key() == "AIza...tKey"
    
    empty_set = Settings(GEMINI_API_KEY=None, OPENAI_API_KEY=None)
    assert empty_set.get_masked_api_key() == "NOT_SET"

def test_logger_creation():
    """Verify logger creation and configuration."""
    test_log = get_logger("test_module")
    assert test_log.name == "test_module"
    assert len(test_log.handlers) > 0
