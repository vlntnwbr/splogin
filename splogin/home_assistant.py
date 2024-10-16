"""Handler and entrypoint for Home Assistant API."""

from logging import Logger
from typing import Any

import requests

from . import (
    CredentialManager,
    CredentialsError,
    HomeAssistantApiError
)


class HomeAssistant(CredentialManager):
    """Wrapper for Home Assistant API interactions."""

    SERVICE_NAME = "splogin-hass"
    SERVICE_ALIAS = "Home Assistant"
    SECRET_ALIAS = "instance"  # nosec
    SECRET_TYPE = "token"  # nosec
    USER_ALIAS = "instance_url"

    def __init__(self, logger: Logger) -> None:
        """Create handler and ensure authenticated API availability."""
        try:
            super().__init__(logger)
        except CredentialsError as exc:
            raise CredentialsError(
                "No Home Assistant Instance configured"
            ) from exc
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
            raise HomeAssistantApiError(
                f"Home Assistant '{self.api_url}' is unreachable"
            ) from exc
        except requests.RequestException as exc:
            raise HomeAssistantApiError(
                f"Home Assistant API returned {response.status_code}"
            ) from exc

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
            raise HomeAssistantApiError(
                f"Home Assistant returned {response.status_code}"
                f"when triggering {event}"
            ) from exc

    @property
    def base_headers(self) -> dict[str, Any]:
        """Return headers dictionary with Authorization Header."""
        return {"Authorization": "Bearer " + self.credentials.password}
