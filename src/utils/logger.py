import logging
import sys
from src.config import settings

def get_logger(name: str) -> logging.Logger:
    """Configures and returns a logger instance for the specified module name."""
    logger = logging.getLogger(name)
    
    # Avoid adding duplicate handlers if logger is already initialized
    if not logger.handlers:
        logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
        
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger

# Global default logger
logger = get_logger("ai_expense_audit")
