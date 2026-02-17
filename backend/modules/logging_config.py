"""
Logging Configuration for AI Automation System
Provides centralized, structured logging with file rotation and colored console output
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime


# Create logs directory
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Log file path
LOG_FILE = LOGS_DIR / "ai_automation.log"


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # ASCII-safe prefixes (emojis crash on Windows cp1258/charmap)
    PREFIX = {
        'DEBUG': '[DBG]',
        'INFO': '[OK]',
        'WARNING': '[WARN]',
        'ERROR': '[ERR]',
        'CRITICAL': '[CRIT]',
    }
    
    def format(self, record: logging.LogRecord) -> str:
        try:
            # Add color and prefix for console
            color = self.COLORS.get(record.levelname, '')
            prefix = self.PREFIX.get(record.levelname, '')
            
            # Format timestamp
            timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
            
            # Build message - strip any emoji from the message itself for safe console output
            msg = record.getMessage()
            
            message = f"{color}{prefix} [{timestamp}] {record.name}: {msg}{self.RESET}"
            
            # Add exception info if present
            if record.exc_info:
                message += f"\n{self._formatException(record.exc_info)}"
            
            return message
        except Exception:
            # Ultimate fallback - if formatting fails, return plain ASCII
            try:
                safe_msg = record.getMessage().encode('ascii', 'replace').decode('ascii')
                return f"[{record.levelname}] {record.name}: {safe_msg}"
            except Exception:
                return f"[{record.levelname}] {record.name}: (message encoding error)"


class FileFormatter(logging.Formatter):
    """Formatter for file logging (no colors, full timestamp)"""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


class SafeStreamHandler(logging.StreamHandler):
    """Stream handler that won't crash on Windows codepage encoding errors.
    
    Windows consoles using cp1258/charmap can't display emoji characters,
    causing UnicodeEncodeError which crashes the entire application if uncaught.
    This handler catches encoding errors and falls back to ASCII-safe output.
    """
    
    def emit(self, record):
        try:
            super().emit(record)
        except UnicodeEncodeError:
            # Strip non-ASCII characters and try again
            try:
                record.msg = record.msg.encode('ascii', 'replace').decode('ascii') if isinstance(record.msg, str) else record.msg
                super().emit(record)
            except Exception:
                pass  # Silently drop the log message rather than crash
        except Exception:
            self.handleError(record)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Get a configured logger instance
    
    Args:
        name: Logger name (usually __name__ of the module)
        level: Logging level (default: INFO)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Console handler with safe encoding (prevents Windows codepage crashes)
    console_handler = SafeStreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)
    
    # File handler with rotation (10MB max, 5 backups)
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # Log everything to file
        file_handler.setFormatter(FileFormatter())
        logger.addHandler(file_handler)
    except Exception as e:
        # If file logging fails, continue with console only
        logger.warning(f"Could not set up file logging: {e}")
    
    return logger


# Pre-configured loggers for main modules
def get_gpm_logger() -> logging.Logger:
    """Logger for GPM Profile Manager"""
    return get_logger("gpm.profile_manager")


def get_wizard_logger() -> logging.Logger:
    """Logger for Account Wizard"""
    return get_logger("gpm.account_wizard")


def get_automation_logger() -> logging.Logger:
    """Logger for AI Automation"""
    return get_logger("ai.automation")


def get_scheduler_logger() -> logging.Logger:
    """Logger for Session Scheduler"""
    return get_logger("ai.scheduler")


# Convenience function to set log level globally
def set_log_level(level: str):
    """
    Set log level for all AI automation loggers
    
    Args:
        level: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    for logger_name in ['gpm.profile_manager', 'gpm.account_wizard', 
                        'ai.automation', 'ai.scheduler']:
        logger = logging.getLogger(logger_name)
        logger.setLevel(numeric_level)
        for handler in logger.handlers:
            handler.setLevel(numeric_level)
