from getpass import getpass
from logging import Logger
from typing import Any

import keyring
import requests


from . import CredentialsException, get_logger, log_error

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
        return self.instance_url

    @classmethod
    def make_instance(
        cls,
        log: Logger,
        url: str,
        token: str | None
    ) -> 'HomeAssistant':
        try:
            existing = cls(log)
            log.info("deleting existing instance %s", existing)
            keyring.delete_password(existing.SERVICE_NAME, existing.instance_url)
        except (CredentialsException, HomeAssistantApiException):
            pass
        token = getpass("Enter Token: ") if token is None else token
        keyring.set_password(cls.SERVICE_NAME, username=url, password=token)
        return cls(log)
        
    def check_api_connection(self) -> bool:
        # TODO use method for api request with error handling
        try:
            response = requests.get(self.instance_url, headers=self.base_headers)
            response.raise_for_status()
        except requests.ConnectionError as exc:
            raise HomeAssistantApiException(
                f"Home Assistant '{self.instance_url}' is unreachable"
            ) from exc
        except requests.RequestException as exc:
            raise HomeAssistantApiException(exc) from exc

    # TODO add method for triggering a Home Assistant event
    
    @property
    def base_headers(self) -> dict[str, Any]:
        return {"Authorization": "Bearer " + self.token}
    
    
def main(args) -> None:
    log = get_logger(HomeAssistant.SERVICE_NAME, args.log_level)
    log.debug(args)
    try:
        log.debug("connecting to Home Assistant")
        hass = HomeAssistant.make_instance(log, args.instance_url, args.token)
        log.info("created Home Assistance instance '%s'", hass.instance_url)
    except (CredentialsException, HomeAssistantApiException) as exc:
        log_error(log, exc)
