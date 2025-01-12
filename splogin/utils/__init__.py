"""Package for utilities used by splogin."""

import logging
import subprocess  # nosec
import sys

from .errors import BrowserUnavailableError


def get_logger(name: str, level: int | str) -> logging.Logger:
    """Create a named, formatted logger for the given level."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = logging.Formatter(
        "%(name)s %(levelname)8s - %(message)s"
    )
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger


def log_error(
    log: logging.Logger,
    exc: Exception,
    message: str | None = None,
) -> None:
    """Error log the (exception) message. Debug log the traceback."""
    log.error(exc if message is None else message)
    log.debug(exc.__class__, exc_info=True)


def playwright_install(browser: str = "firefox") -> None:
    """Install browser using playwright cli in the python directory."""
    try:
        subprocess.run(  # nosec
            (sys.executable, "-m", "playwright", "install", browser),
            check=True
        )
    except subprocess.CalledProcessError as exc:
        raise BrowserUnavailableError(
            "Failed to install browser for playwright"
        ) from exc
