"""Main package for splogin with common utilities."""

import getpass
import logging

import keyring

from keyring.errors import PasswordDeleteError

# TODO make new SpotifyLogin class from CredentialManager
#   - add method for performing spotify login
#   - this will be the new user command
# TODO ensure classes only log to debug level


class CredentialsException(BaseException):  # TODO Refactor to Credential
    """Raised when credentials for a needed action are missing."""


class CredentialManager:
    """Wrapper for keyring to manage a single piece of credentials."""

    SERVICE_NAME: str | None = None

    def __init__(
        self,
        logger: logging.Logger,
    ) -> None:
        """Load credentials for cls.SERVICE_NAME."""
        if self.SERVICE_NAME is None:
            raise NotImplementedError(
                "CredentialManager must be instantiated from subclass "
                "with valid cls.SERVICE_NAME"
            )
        self.log = logger
        credentials = keyring.get_credential(self.SERVICE_NAME, None)
        if credentials is None:
            raise CredentialsException(f"{self.SERVICE_NAME}: no credentials")
        self.credentials = credentials

    def __str__(self) -> str:
        """Return the credentials username."""
        return self.credentials.username

    def delete(self) -> str:
        """Delete the existing credentials and return username."""
        keyring.delete_password(self.SERVICE_NAME, self.credentials.username)
        return self.credentials.username

    @classmethod
    def make(
        cls,
        log: logging.Logger,
        username: str,
        password: str | None = None,
        password_alias: str = "Password"
    ) -> tuple['CredentialManager', str]:
        """Create new credentials after removing existing ones."""
        try:
            operation = "update"
            keyring.delete_password(cls.SERVICE_NAME, username)
            log.debug("deleted existing %s: %s", cls.SERVICE_NAME, username)
        except PasswordDeleteError:
            operation = "create"
        if password is None:
            password = getpass.getpass(f"Enter {password_alias}: ").strip()
        keyring.set_password(cls.SERVICE_NAME, username, password)
        return cls(log), operation


def get_logger(name: str, level: int | str) -> logging.Logger:
    """Create a named, formatted logger for the given level."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = logging.Formatter(
        "%(name)s - %(levelname)-8s - %(message)s"
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
