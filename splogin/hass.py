"""Handler and entrypoint for Home Assistant API."""

from argparse import Namespace
from getpass import getpass
from logging import Logger
from typing import Any

import keyring
import keyring.errors
import requests

from . import CredentialsException, get_logger, log_error

# TODO delete existing instance


class HomeAssistantApiException(BaseException):
    """Raised when an error during Home Assistant API calls occurs."""


class HomeAssistant:
    """Wrapper for Home Assistant API interactions."""

    SERVICE_NAME = "splogin-hass"

    def __init__(
        self,
        logger: Logger,
    ) -> None:
        """Create handler and ensure authenticated API availability."""
        self.log = logger
        self.log.debug("fetching Home Assistant instance")
        credentials = keyring.get_credential(self.SERVICE_NAME, None)
        if credentials is None:
            raise CredentialsException("can't find Home Assistant instance")
        self.log.debug("found instance %r", credentials)
        self.instance_url = credentials.username
        self.api_url = self.instance_url + "/api/"
        self.token = credentials.password

        self.check_api_connection()

    def __str__(self) -> str:
        """Return the Home Assistant URL without trailing '/api/'."""
        return self.instance_url

    @classmethod
    def make_instance(
        cls,
        log: Logger,
        url: str,
        token: str | None
    ) -> tuple['HomeAssistant', str]:
        """Create or Update the Home Assistant API instance."""
        try:
            operation = "update"
            keyring.delete_password(cls.SERVICE_NAME, url)
            log.debug("deleted existing Home Assistant instance %s", url)
        except keyring.errors.PasswordDeleteError:
            operation = "create"
        token = getpass("Enter Token: ") if token is None else token
        keyring.set_password(cls.SERVICE_NAME, url, token)
        return cls(log), operation
        
    def delete_instance(self) -> str:
        """Delete the existing instance from keyring and return URL."""
        keyring.delete_password(self.SERVICE_NAME, self.instance_url)
        return self.instance_url
    
    def check_api_connection(self) -> bool:
        """Return True after successful Home Assistant API call."""
        try:
            response = requests.get(
                self.api_url,
                headers=self.base_headers,
                timeout=10
            )
            self.log.debug(
                "%d: headers=%r; content=%r",
                response.status_code,
                response.headers,
                response.content
            )
            response.raise_for_status()
        except requests.ConnectionError as exc:
            raise HomeAssistantApiException(
                f"Home Assistant '{self.api_url}' is unreachable"
            ) from exc
        except requests.RequestException as exc:
            raise HomeAssistantApiException(exc) from exc

    def trigger_event(self, event: str, payload: dict[str, Any]):
        """Trigger a Home Assistant event with a json payload."""
        try:
            self.log.debug("triggering event: %s. Payload %r", event, payload)
            response = requests.post(
                self.api_url + "events/" + event,
                json=payload,
                timeout=10,
                headers={
                    **self.base_headers,
                    "Content-Type": "application/json"
                }
            )
            self.log.debug(
                "%d: headers=%r; content=%r",
                response.status_code,
                response.headers,
                response.content
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise HomeAssistantApiException("unable to trigger event") from exc

    @property
    def base_headers(self) -> dict[str, Any]:
        """Return headers dictionary with Authorization Header."""
        return {"Authorization": "Bearer " + self.token}


def main(args: Namespace) -> None:
    """Entrypoint for the splogin subcommand 'hass'."""
    log = get_logger(HomeAssistant.SERVICE_NAME, args.log_level)
    log.debug(args)
    try:
        log.info("Setting Home Assistant instance")
        hass, operation = HomeAssistant.make_instance(
            log,
            args.instance_url,
            args.token
        )
        log.info(
            "%sd Home Assistance instance '%s'",
            hass.instance_url, operation.capitalize()
        )
    except (
        CredentialsException,
        HomeAssistantApiException,
        keyring.errors.KeyringError
    ) as exc:
        log_error(log, exc)
