"""Main package for splogin with common utilities."""

import argparse
import dataclasses
import getpass
import logging

import keyring

from keyring.errors import KeyringError, PasswordDeleteError


class HomeAssistantApiError(BaseException):
    """Raised for errors during Home Assistant API calls."""


class BrowserUnavailableError(BaseException):
    """Raised when an error occurs during playwright browser launch."""


class CredentialsError(BaseException):
    """Raised when credentials for a needed action are missing."""


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


@dataclasses.dataclass(frozen=True, repr=True)
class SpotifyAuthCookie:
    """Container for the Spotify Session cookie values."""

    sp_dc: str
    sp_key: str


class CredentialManager:
    """Wrapper for keyring to manage a single piece of credentials."""

    SERVICE_NAME: str | None
    SERVICE_ALIAS: str | None
    SECRET_ALIAS: str | None
    SECRET_TYPE: str | None
    USER_ALIAS: str | None

    def __init__(
        self,
        logger: logging.Logger,
    ) -> None:
        """Load credentials for cls.SERVICE_NAME."""
        self._raise_for_missing_service_name()
        self.log = logger
        credentials = keyring.get_credential(self.SERVICE_NAME, None)
        if credentials is None:
            raise CredentialsError(f"{self.SERVICE_NAME}: no credentials")
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
    ) -> tuple['CredentialManager', str]:
        """Create new credentials after removing existing ones."""
        try:
            operation = "Updated"
            keyring.delete_password(cls.SERVICE_NAME, username)
            log.debug("deleted existing %s: %s", cls.SERVICE_NAME, username)
        except PasswordDeleteError:
            operation = "Created"
        if password is None:
            password = getpass.getpass(f"Enter {cls.SECRET_ALIAS}: ").strip()
        keyring.set_password(cls.SERVICE_NAME, username, password)
        return cls(log), operation

    @classmethod
    def cli(cls, args: argparse.Namespace) -> None:
        """Entrypoint for splogin credential management subcommands."""
        log = get_logger(cls.SERVICE_NAME, args.log_level)
        log.debug(args)
        try:
            username = getattr(args, cls.USER_ALIAS.replace("-", "_"))
            if username == "rm":
                credentials = cls(log)
                credentials.delete()
                operation = "Deleted"
            else:
                credentials, operation = cls.make(log, username, args.password)
            log.info(
                "%s %s %s '%s'",
                operation,
                credentials.SERVICE_ALIAS,
                credentials.SERVICE_ALIAS.capitalize(),
                credentials
            )
        except (
            CredentialsError,
            BrowserUnavailableError,
            HomeAssistantApiError,
            KeyringError
        ) as exc:
            log_error(log, exc)

    @classmethod
    def _raise_for_missing_service_name(cls) -> None:
        """Raise an error when the CredentialManager has no name."""
        if cls.SERVICE_NAME is None:
            raise NotImplementedError(
                "CredentialManager must be used from subclass "
                "with a defined cls.SERVICE_NAME"
            )
