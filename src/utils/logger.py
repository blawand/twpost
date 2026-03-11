import logging
import logging.handlers
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s"


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


def setup_logger(logger_name=None):
    """Sets up a logger with console output. Call once at startup."""
    log_level = getattr(logging, LOG_LEVEL, logging.INFO)

    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)

    # Remove existing handlers to prevent duplication
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    console_handler = SafeStreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console_handler)
