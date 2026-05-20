"""
Comprehensive logging system for Slay the Spire Voice Recorder.

Features:
- Daily log folders (logs/YYYY-MM-DD/)
- Component-specific log files
- Millisecond timestamps
- Function name and line number tracking
- Auto-rotation (10 MB per file, 7 days retention)
"""

import sys
from pathlib import Path
from datetime import datetime
from loguru import logger
from typing import Optional

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent


class LoggerConfig:
    """Configuration for the logging system."""
    
    # Log base directory
    LOG_BASE_DIR = PROJECT_ROOT / "logs"
    
    # Component-specific log files
    COMPONENTS = {
        "backup": "backup_operations.log",
        "parsing": "save_parsing.log",
        "voice": "voice_recording.log",
        "llm": "llm_corrections.log",
        "summary": "summary_updates.log",
        "errors": "errors.log",
    }
    
    # Log format with milliseconds, function, and line number
    LOG_FORMAT = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # Rotation settings
    ROTATION = "10 MB"
    RETENTION = "7 days"
    
    # Log level
    LEVEL = "DEBUG"


def setup_logger(component: str = "general") -> logger:
    """
    Set up a logger for a specific component.
    
    Args:
        component: Component name (backup, parsing, voice, llm, summary, errors)
        
    Returns:
        Configured logger instance
    """
    # Create daily log directory
    daily_dir = LoggerConfig.LOG_BASE_DIR / datetime.now().strftime("%Y-%m-%d")
    daily_dir.mkdir(parents=True, exist_ok=True)
    
    # Get component log filename
    log_filename = LoggerConfig.COMPONENTS.get(component, f"{component}.log")
    log_path = daily_dir / log_filename
    
    # Remove default handler
    logger.remove()
    
    # Terminal output suppressed - logs only go to files
    # (User sees only essential print() statements from main script)
    
    # Add file handler for component-specific logs
    logger.add(
        log_path,
        format=LoggerConfig.LOG_FORMAT,
        level=LoggerConfig.LEVEL,
        rotation=LoggerConfig.ROTATION,
        retention=LoggerConfig.RETENTION,
        encoding="utf-8",
    )
    
    # Add separate error log (all components write to errors.log too)
    error_log_path = daily_dir / "errors.log"
    logger.add(
        error_log_path,
        format=LoggerConfig.LOG_FORMAT,
        level="ERROR",
        rotation=LoggerConfig.ROTATION,
        retention=LoggerConfig.RETENTION,
        encoding="utf-8",
    )
    
    logger.info(f"Logger initialized for component: {component}")
    logger.info(f"Log file: {log_path}")
    
    return logger


def log_operation(
    log: logger,
    operation: str,
    details: dict,
    level: str = "INFO"
) -> None:
    """
    Log an operation with structured details.
    
    Args:
        log: Logger instance
        operation: Operation name (e.g., "backup_created", "file_parsed")
        details: Dictionary of operation details
        level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    # Format details as key=value pairs
    detail_str = " | ".join(f"{k}={v}" for k, v in details.items())
    message = f"{operation} | {detail_str}"
    
    # Log at appropriate level
    if level == "DEBUG":
        log.debug(message)
    elif level == "INFO":
        log.info(message)
    elif level == "WARNING":
        log.warning(message)
    elif level == "ERROR":
        log.error(message)
    else:
        log.info(message)


# Create a default logger instance
default_logger = setup_logger("general")


if __name__ == "__main__":
    # Test the logging system
    test_logger = setup_logger("test")
    
    test_logger.debug("This is a debug message")
    test_logger.info("This is an info message")
    test_logger.warning("This is a warning message")
    test_logger.error("This is an error message")
    
    # Test structured logging
    log_operation(
        test_logger,
        "test_operation",
        {
            "file": "test.txt",
            "size": "1024 bytes",
            "duration": "0.5s"
        }
    )
    
    print(f"\nLogs written to: {LoggerConfig.LOG_BASE_DIR / datetime.now().strftime('%Y-%m-%d')}")
