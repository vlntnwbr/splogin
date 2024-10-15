"""Handler and entrypoint for splogin validation and initialization."""

from . import CredentialsException, get_logger
from .credentials import CredentialManager
from .hass import HomeAssistant, HomeAssistantApiException
from .splogin import check_browser_launch

# TODO method for playwright firefox installation
# TODO add --init option that fixes every error


def main(args):
    """Entrypoint for splogin subcommand 'validate'."""
    service_name = "splogin-validate"
    log = get_logger(service_name, args.log_level)
    log.debug(args)

    try:
        log.info("Checking Spotify credentials")
        credentials = CredentialManager("splogin-user")
        log.info("Using Spotify User: %s", credentials.username)
    except CredentialsException:
        log.warning("Spotify User Not Set")

    if check_browser_launch():
        log.info("Browser for playwright is installed")
    else:
        log.warning("Found no usable Browser for playwright")

    try:
        hass = HomeAssistant(log)
        log.info("Using Home Assistant instance: %s", hass)
    except (CredentialsException, HomeAssistantApiException) as exc:
        log.warning(exc)
