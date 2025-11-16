"""
Centralized logging configuration for Drafter application.
Import this module to get a properly configured logger.

Usage:
    from logger_config import get_logger
    logger = get_logger(__name__)
    logger.info("This goes to file only")
    logger.warning("This goes to both file and console")
"""

import logging
from pathlib import Path


def setup_logging(log_file: str = 'drafter.log', console_level: int = logging.WARNING):
    """
    Configure logging for the entire application.
    
    Args:
        log_file: Path to log file
        console_level: Minimum level for console output (default: WARNING)
    """
    # Create log directory if needed
    log_path = Path(log_file)
    log_path.parent.mkdir(exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear any existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # File handler - logs everything (INFO and above)
    file_handler = logging.FileHandler(log_file, mode='a')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Console handler - only warnings and errors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Silence noisy third-party loggers
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Usually __name__ of the calling module
        
    Returns:
        Configured logger instance
        
    Example:
        logger = get_logger(__name__)
        logger.info("Starting process")  # Goes to file only
        logger.error("Something failed")  # Goes to file and console
    """
    return logging.getLogger(name)


# Initialize logging when module is imported
setup_logging()