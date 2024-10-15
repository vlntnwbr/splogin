"""Handler and entrypoint for Home Assistant API."""

from argparse import Namespace
from logging import Logger
from typing import Any

import keyring
import keyring.errors
import requests

from . import CredentialManager, CredentialsException, get_logger, log_error

# TODO delete existing instance


class HomeAssistantApiException(BaseException):
    """Raised when an error during Home Assistant API calls occurs."""


class HomeAssistant(CredentialManager):
    """Wrapper for Home Assistant API interactions."""

    SERVICE_NAME = "splogin-hass"

    def __init__(
        self,
        logger: Logger,
    ) -> None:
        """Create handler and ensure authenticated API availability."""
        super().__init__(logger)
        self.api_url = self.credentials.username + "/api/"
        self.check_api_connection()

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
        return {"Authorization": "Bearer " + self.credentials.password}


def main(args: Namespace) -> None:
    """Entrypoint for the splogin subcommand 'hass'."""
    log = get_logger(HomeAssistant.SERVICE_NAME, args.log_level)
    log.debug(args)
    try:
        log.info("Setting Home Assistant instance")
        hass, operation = HomeAssistant.make(
            log,
            args.instance_url,
            args.token,
            "Token"
        )
        log.info(
            "%sd Home Assistance instance '%s'",
            operation.capitalize(),
            hass
        )
    except (
        CredentialsException,
        HomeAssistantApiException,
        keyring.errors.KeyringError
    ) as exc:
        log_error(log, exc)
