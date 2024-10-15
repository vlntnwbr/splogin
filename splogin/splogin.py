"""Handler and entrypoint for main splogin functionality."""

import logging

from argparse import Namespace

from playwright.sync_api import sync_playwright

from . import CredentialsException, get_logger, log_error
from .credentials import CredentialManager


class BrowserNotFoundException(BaseException):
    """Raised when an error occurs during playwright browser launch."""


class SpotifyLoginFailed(BaseException):
    """Raised when the automated Spotify Web login fails."""


def check_browser_launch() -> bool:
    """Return True if playwright browser launch succeeds."""
    with sync_playwright() as playwright:
        try:
            browser = playwright.firefox.launch()
            browser.close()
            return True
        except:
            return False


class SpLogin:
    """Handler for automated Spotify Web Login and cookie extraction."""

    def __init__(
        self,
        logger: logging.Logger,
        spotify_auth: CredentialManager,
        spotify_login_button: str,
        spotify_login_page: str,
        spotify_username_field: str,
        spotify_password_field: str
    ):
        """Create handler and ensure browser availability."""
        if not check_browser_launch():
            raise BrowserNotFoundException("cannot locate browser")

        self.log = logger
        self.sp_auth = spotify_auth

        self._sp_login_page = spotify_login_page
        self._sp_user_field = spotify_username_field
        self._sp_pswd_field = spotify_password_field
        self._sp_login_button = spotify_login_button

    def perform_spotify_login(self) -> tuple[str, str]:
        """Extract sp_dc & sp_key cookies after Spotify Web Login."""
        # TODO exception handling
        # TODO better logging
        with sync_playwright() as playwright:

            browser = playwright.firefox.launch()
            context = browser.new_context()
            page = context.new_page()

            page.goto(self._sp_login_page)
            self.log.debug("filling credentials for %s", self.sp_auth.username)
            page.fill("input#" + self._sp_user_field, self.sp_auth.username)
            page.fill("input#" + self._sp_pswd_field, self.sp_auth.password)
            self.log.debug("submitting login...")
            page.click("button#" + self._sp_login_button)
            page.wait_for_load_state("networkidle")
            try:
                self.log.debug("extracting cookies")
                cookies = context.cookies()
                sp_dc = next(c for c in cookies if c["name"] == "sp_dc")
                sp_key = next(c for c in cookies if c["name"] == "sp_key")
            except Exception as exc:
                raise SpotifyLoginFailed("cannot extract cookies") from exc
        return sp_dc["value"], sp_key["value"]


def main(args: Namespace) -> None:
    """Entrypoint for the splogin subcommand 'run'."""
    log = get_logger("splogin", args.log_level)
    log.debug(args)
    try:
        log.debug("fetching spotify credentials")
        spotify_auth = CredentialManager("splogin-user")
        app = SpLogin(
            logger=log,
            spotify_auth=spotify_auth,
            spotify_login_button=args.spotify_login_button,
            spotify_login_page=args.spotify_login_page,
            spotify_password_field=args.spotify_password_field,
            spotify_username_field=args.spotify_username_field
        )
        log.info("Performing Spotify Login")
        sp_dc, sp_key = app.perform_spotify_login()
        log.debug("sp_dc  | %s", sp_dc)
        log.debug("sp_key | %s", sp_key)
    except (
        CredentialsException,
        BrowserNotFoundException,
        SpotifyLoginFailed
    ) as exc:
        log_error(log, exc)
