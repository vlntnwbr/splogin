"""Main package for splogin with cli subcommand handlers."""

from argparse import Namespace

from .home_assistant import HomeAssistant
from .spotify import SpotifyWebLogin
from .utils.errors import (
    BrowserUnavailableError,
    CredentialError,
    HomeAssistantApiError
)

from .utils import get_logger


def run(args: Namespace) -> None:
    """Entrypoint for subcommand 'splogin run'."""
    log = get_logger("splogin", args.log_level)
    log.debug(args)


def validate(args):
    """Entrypoint for subcommand 'splogin validate'."""
    # TODO add --init option that fixes every error
    service_name = "splogin-validate"
    log = get_logger(service_name, args.log_level)
    log.debug(args)

    try:
        log.info("Checking Spotify Web login availability")
        spotify_login = SpotifyWebLogin(log)
        log.info("Using Spotify User: %s", spotify_login)
    except CredentialError:
        log.warning("Spotify User Not Set")
    try:
        SpotifyWebLogin.validate_browser_availability()
        log.info("Browser for playwright is installed")
    except BrowserUnavailableError:
        log.warning("Found no usable Browser for playwright")

    try:
        hass = HomeAssistant(log)
        log.info("Using Home Assistant instance: %s", hass)
    except (CredentialError, HomeAssistantApiError) as exc:
        log.warning(exc)
