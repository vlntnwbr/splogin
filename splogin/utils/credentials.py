"""Credential Manager with cli entrypoint."""

import argparse
import getpass
import logging

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

from . import get_logger, log_error
from .errors import CredentialError, SPLoginException


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
            raise CredentialError(f"{self.SERVICE_NAME}: no credentials")
        if credentials.password is None:
            raise CredentialError(
                f"{self.SERVICE_NAME}: no password for {credentials.username}"
            )
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
            password = getpass.getpass(
                f"Enter {cls.SECRET_TYPE.capitalize()}: "
            ).strip()
        keyring.set_password(cls.SERVICE_NAME, username, password)
        return cls(log), operation

    @classmethod
    def cli(cls, args: argparse.Namespace) -> None:
        """Entrypoint for splogin credential management subcommands."""
        log = get_logger(cls.SERVICE_NAME, args.log_level)
        log.debug(args)
        try:
            username = getattr(args, cls.get_username_arg_name())
            if username == "rm":
                credentials = cls(log)
                credentials.delete()
                operation = "Deleted"
            else:
                credentials, operation = cls.make(
                    log,
                    username,
                    getattr(args, "password", None)
                )
            log.info(
                "%s %s %s '%s'",
                operation,
                credentials.SERVICE_ALIAS,
                credentials.SECRET_ALIAS,
                credentials
            )
        except (
            SPLoginException,
            KeyringError
        ) as exc:
            log_error(log, exc)

    @classmethod
    def get_username_input(cls, prompt: str | None = None) -> str:
        """Prompt for user input and return stripped text."""
        # pylint: disable=consider-using-f-string
        return input("Enter {}: ".format(
            prompt if prompt is not None else cls.SECRET_ALIAS.capitalize()
        )).strip()

    @classmethod
    def get_username_arg_name(cls) -> str:
        """Replace '-' with '_' for accessing username arg in cli ."""
        return cls.USER_ALIAS.replace("-", "_")

    @classmethod
    def _raise_for_missing_service_name(cls) -> None:
        """Raise an error when the CredentialManager has no name."""
        if cls.SERVICE_NAME is None:
            raise NotImplementedError(
                "CredentialManager must be used from subclass "
                "with a defined cls.SERVICE_NAME"
            )
