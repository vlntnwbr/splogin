import logging
from typing import Any

import keyring
import requests


from . import CredentialsException, get_logger

class HomeAssistantApiException(BaseException): pass

class HomeAssistant:

    def __init__(
        self,
        logger: logging.Logger,
        instance_url: str,
        service_name: str
    ) -> None:
        self.log = logger
        self.instance_url = instance_url + "/api/"
        self.service_name = service_name
        self.check_api_connection()
        
    def check_api_connection(self) -> bool:
        # TODO use method for aüi request with error handling
        try:
            response = requests.get(self.instance_url, headers=self.base_headers)
            response.raise_for_status()
        except requests.RequestException as exc:
            self.log.error("an error occurred with the api request")
            self.log.debug(exc, exc_info=True)
            raise HomeAssistantApiException(exc) from exc
    
    # TODO add method for api request with error handling

    # TODO add method for triggering a Home Assistant event
    
    @staticmethod
    def set_token(service_name: str, token: str) -> None:
        keyring.set_password(service_name, "bearer-token", token)

    @property
    def base_headers(self) -> dict[str, Any]:
        return {"Authorization": "Bearer " + self.token}
    
    @property
    def token(self) -> str:
        token = keyring.get_password(self.service_name, "bearer-token")
        if token is None:
            raise CredentialsException("missing token for Home Assistant")
        return token


def main(args) -> None:
    service_name = "splogin-hass"
    log = get_logger(service_name, args.log_level)
    try:
        log.debug("connecting to Home Assistant")
        hass = HomeAssistant(log, args.instance_url, service_name)
    except (CredentialsException, HomeAssistantApiException) as exc:
        log.error(exc)
        log.debug(exc, exc_info=True)
