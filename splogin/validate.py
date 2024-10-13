from . import get_logger
from .credentials import CredentialManager, CredentialsException


def validate(args):
    service_name = "splogin-validate"
    log = get_logger(service_name, args.log_level)
    log.debug(args)
    try:
        log.info("checking Spotify credentials")
        credentials = CredentialManager("splogin-user")
        log.info("Using Spotify User: %s", credentials.username)
    except CredentialsException:
        log.warning("Spotify User Not Set")
