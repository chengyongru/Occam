"""
Logger configuration utility
"""
import sys
from loguru import logger


def setup_logger(level: str = "INFO"):
    """
    Setup loguru logger with custom format
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{file.path}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
        level=level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    return logger

