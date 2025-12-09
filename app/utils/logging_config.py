"""Logging configuration utilities"""
import logging
import sys
from typing import Optional

def setup_logger(
    name: str,
    level: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with consistent formatting.
    
    Args:
        name: Logger name (usually __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set level if provided
    if level:
        logger.setLevel(getattr(logging, level.upper()))
    
    # Add handler if not already present
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        
        # Use custom format or default
        if format_string is None:
            format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        formatter = logging.Formatter(format_string)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

def log_user_action(logger: logging.Logger, user_id: int, action: str, details: str = ""):
    """
    Log user action in a consistent format.
    
    Args:
        logger: Logger instance
        user_id: Telegram user ID
        action: Action description
        details: Additional details
    """
    log_msg = f"User {user_id} | {action}"
    if details:
        log_msg += f" | {details}"
    logger.info(log_msg)

def log_error_with_context(
    logger: logging.Logger,
    error: Exception,
    context: str,
    user_id: Optional[int] = None
):
    """
    Log error with context information.
    
    Args:
        logger: Logger instance
        error: Exception object
        context: Context description
        user_id: Optional user ID
    """
    user_info = f"User {user_id} | " if user_id else ""
    logger.error(
        f"{user_info}{context}: {type(error).__name__}: {str(error)}",
        exc_info=True
    )
