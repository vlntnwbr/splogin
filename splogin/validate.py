from . import get_logger

from .credentials import CredentialManager, CredentialsException
from .splogin import check_browser_launch

def main(args):
    service_name = "splogin-validate"
    log = get_logger(service_name, args.log_level)
    log.debug(args)
    
    try:
        log.info("checking Spotify credentials")
        credentials = CredentialManager("splogin-user")
        log.info("Using Spotify User: %s", credentials.username)
    except CredentialsException:
        log.warning("Spotify User Not Set")
    
    if check_browser_launch():
        log.info("playwright browser is working")
    else:
        log.warning("playwright cannot locate browser")
