from getpass import getpass
from logging import Logger
from typing import Any

import keyring
import keyring.errors
import requests

from . import CredentialsException, get_logger, log_error

# TODO add exception handling for keyring

class HomeAssistantApiException(BaseException): pass

class HomeAssistant:

    SERVICE_NAME = "splogin-hass"

    def __init__(
        self,
        logger: Logger,
    ) -> None:
        self.log = logger
        self.log.debug("fetching Home Assistant instance")
        credentials = keyring.get_credential(self.SERVICE_NAME, None)
        if credentials is None:
            raise CredentialsException("can't find Home Assistant instance")
        self.log.debug("found instance %r", credentials)
        self.instance_url = credentials.username + "/api/"
        self.token = credentials.password

        self.check_api_connection()

    def __str__(self) -> str:
        return self.instance_url[:-5]

    @classmethod
    def make_instance(
        cls,
        log: Logger,
        url: str,
        token: str | None
    ) -> 'HomeAssistant':
        try:
            keyring.delete_password(cls.SERVICE_NAME, url)
            log.warning("Deleted existing Home Assistant instance %s", url)
        except (keyring.errors.PasswordDeleteError):
            pass
        token = getpass("Enter Token: ") if token is None else token
        keyring.set_password(cls.SERVICE_NAME, username=url, password=token)
        return cls(log)
        
    def check_api_connection(self) -> bool:
        try:
            response = requests.get(self.instance_url, headers=self.base_headers)
            response.raise_for_status()
            self.log.info("Home Assistant '%s' is available", self.instance_url)
        except requests.ConnectionError as exc:
            raise HomeAssistantApiException(
                f"Home Assistant '{self.instance_url}' is unreachable"
            ) from exc
        except requests.RequestException as exc:
            raise HomeAssistantApiException(exc) from exc

    def trigger_event(self, event: str, payload: dict[str, Any]):
        try:
            self.log.debug("triggering event: %s with payload %r", event, payload)
            response = requests.post(
                self.instance_url + "events/" + event,
                json=payload,
                headers={
                    **self.base_headers,
                    "Content-Type": "application/json"
            })
            response.raise_for_status()
        except requests.RequestException as exc:
            raise HomeAssistantApiException("unable to trigger event") from exc
    
    @property
    def base_headers(self) -> dict[str, Any]:
        return {"Authorization": "Bearer " + self.token}

    
def main(args) -> None:
    log = get_logger(HomeAssistant.SERVICE_NAME, args.log_level)
    log.debug(args)
    try:
        log.info("Setting Home Assistant instance")
        hass = HomeAssistant.make_instance(log, args.instance_url, args.token)
        log.info("Using Home Assistance instance '%s'", hass.instance_url)
    except (CredentialsException, HomeAssistantApiException) as exc:
        log_error(log, exc)
