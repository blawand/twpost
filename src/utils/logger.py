import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from core.config_loader import ConfigLoader

# Define project root relative to this file's location (src/utils/logger.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class SafeStreamHandler(logging.StreamHandler):
    """Stream handler that degrades unsupported console characters safely."""

    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            encoding = getattr(stream, "encoding", None) or "utf-8"
            safe_msg = msg.encode(encoding, errors="replace").decode(encoding, errors="replace")
            stream.write(safe_msg + self.terminator)
            self.flush()
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)


def setup_logger(config_loader: Optional[ConfigLoader] = None, logger_name: Optional[str] = None):
    """
    Sets up a logger (root logger by default) based on configuration.
    This function should ideally be called once at application startup.
    """
    if config_loader is None:
        config_loader = ConfigLoader()

    # --- General Logging Settings ---
    default_log_level_str = config_loader.get_logging_setting('level', 'INFO').upper()
    default_log_format = config_loader.get_logging_setting(
        'format', 
        '%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s'
    )
    log_level = getattr(logging, default_log_level_str, logging.INFO)

    # Get the target logger; if logger_name is None, it's the root logger.
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level) # Set the base level for the logger itself

    # Remove existing handlers from this specific logger to prevent duplication
    # if this function is called multiple times for the same logger.
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Prevent logs from propagating to the root logger's handlers if this is not the root logger
    # and the root logger has its own handlers. This gives more control.
    if logger_name is not None: # If it's a named logger (not root)
        logger.propagate = config_loader.get_logging_setting('propagate', False)


    # --- Console Handler Settings ---
    console_handler_config = config_loader.get_logging_setting('console_handler', {})
    if console_handler_config.get('enabled', True): # Enabled by default
        console_log_level_str = console_handler_config.get('level', default_log_level_str).upper()
        console_log_format = console_handler_config.get('format', default_log_format)
        console_log_level = getattr(logging, console_log_level_str, log_level)

        console_handler = SafeStreamHandler(sys.stdout)
        console_handler.setLevel(console_log_level)
        console_handler.setFormatter(logging.Formatter(console_log_format))
        logger.addHandler(console_handler)

    # --- File Handler Settings ---
    file_handler_config = config_loader.get_logging_setting('file_handler', {})
    if file_handler_config.get('enabled', False): # Disabled by default, explicit enable needed
        log_file_path_str = file_handler_config.get('path', 'logs/app.log')
        log_file_path = PROJECT_ROOT / log_file_path_str

        # Ensure log directory exists
        try:
            log_file_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            # Use a basic print here as logger might not be fully set up or could cause recursion
            print(f"Error: Could not create log directory {log_file_path.parent}. File logging disabled. Error: {e}", file=sys.stderr)
            return # Exit if we can't create log dir

        file_log_level_str = file_handler_config.get('level', default_log_level_str).upper()
        file_log_format = file_handler_config.get('format', default_log_format)
        file_log_level = getattr(logging, file_log_level_str, log_level)

        # Rotation settings
        rotation_type = file_handler_config.get('rotation_type', None) # e.g., 'size', 'time'
        max_bytes = int(file_handler_config.get('max_bytes', 1024 * 1024 * 5)) # 5MB default
        backup_count = int(file_handler_config.get('backup_count', 5))
        when = file_handler_config.get('when', 'midnight') # For TimedRotatingFileHandler
        interval = int(file_handler_config.get('interval', 1)) # For TimedRotatingFileHandler

        if rotation_type == 'size':
            file_handler = logging.handlers.RotatingFileHandler(
                log_file_path, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8'
            )
        elif rotation_type == 'time':
            file_handler = logging.handlers.TimedRotatingFileHandler(
                log_file_path, when=when, interval=interval, backupCount=backup_count, encoding='utf-8'
            )
        else: # No rotation or invalid type
            file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        
        file_handler.setLevel(file_log_level)
        file_handler.setFormatter(logging.Formatter(file_log_format))
        logger.addHandler(file_handler)
    
    # If no handlers were added at all (e.g., both console and file disabled)
    # add a NullHandler to prevent "No handlers could be found" warnings.
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())

