"""Main package for splogin with cli subcommand handlers."""

from argparse import Namespace

from .home_assistant import HomeAssistant
from .spotify import SpotifyWebLogin
from .utils import get_logger, log_error, playwright_install
from .utils.errors import (
    BrowserUnavailableError,
    CredentialError,
    HomeAssistantApiError
)


def run(args: Namespace) -> None:
    """Entrypoint for subcommand 'splogin run'."""
    log = get_logger("splogin", args.log_level)
    log.debug(args)


def validate(args: Namespace):
    """Entrypoint for subcommand 'splogin validate'."""
    service_name = getattr(args, "service_name", "splogin-validate")
    log = get_logger(service_name, args.log_level)
    log.debug(args)

    log.info("Checking existence and validity of Home Assistant instance")
    try:
        hass = HomeAssistant(log)
        log.info("Using Home Assistant instance: %s", hass)
    except (CredentialError, HomeAssistantApiError) as exc:
        if isinstance(exc, CredentialError) and args.fix:
            log.warning("No instance found. Creating now...")
            setattr(
                args,
                HomeAssistant.get_username_arg_name(),
                HomeAssistant.get_username_input()
            )
            HomeAssistant.cli(args)
        else:
            log.warning(exc)

    log.info("Checking existence of credentials for Spotify Web login")
    try:
        spotify_login = SpotifyWebLogin(log)
        log.info("Using Spotify User: %s", spotify_login)
    except CredentialError:
        log.warning("No valid credentials found. Creating now...")
        if args.fix:
            setattr(
                args,
                SpotifyWebLogin.get_username_arg_name(),
                SpotifyWebLogin.get_username_input("Spotify Email or username")
            )
            SpotifyWebLogin.cli(args)
        else:
            log.warning("Spotify User Not Set")

    log.info("Checking Browser availability for Spotify Web Login")
    try:
        SpotifyWebLogin.validate_browser_availability()
        log.info("Browser for playwright is installed")
    except BrowserUnavailableError:
        log.warning("Found no usable Browser for playwright")
        if args.fix:
            try:
                playwright_install()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                log_error(log, exc, "Cannot install browser for playwright.")
