"""Handler and entrypoint for splogin validation and initialization."""

from . import BrowserUnavailableError, CredentialsError, get_logger
from .home_assistant import HomeAssistant, HomeAssistantApiError
from .spotify import SpotifyWebLogin


def main(args):
    """Entrypoint for splogin subcommand 'validate'."""
    service_name = "splogin-validate"
    log = get_logger(service_name, args.log_level)
    log.debug(args)

    try:
        log.info("Checking Spotify Web login availability")
        spotify_login = SpotifyWebLogin(log)
        log.info("Using Spotify User: %s", spotify_login)
    except CredentialsError:
        log.warning("Spotify User Not Set")
    try:
        SpotifyWebLogin.validate_browser_availability()
        log.info("Browser for playwright is installed")
    except BrowserUnavailableError:
        log.warning("Found no usable Browser for playwright")

    try:
        hass = HomeAssistant(log)
        log.info("Using Home Assistant instance: %s", hass)
    except (CredentialsError, HomeAssistantApiError) as exc:
        log.warning(exc)
