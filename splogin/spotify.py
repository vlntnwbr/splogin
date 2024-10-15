"""Handler and entrypoint for automated Spotify Web login."""

from argparse import Namespace
from logging import Logger

from playwright.sync_api import sync_playwright

from . import (
    BrowserUnavailableError,
    CredentialsException,
    CredentialManager,
    get_logger,
    log_error,
    SpotifyAuthCookie
)


class SpotifyLoginError(BaseException):
    """Raised for errors during automated Spotify Web login."""


class SpotifyWebLogin(CredentialManager):
    """Handler for automated Spotify Web login and cookie extraction."""

    SERVICE_NAME = "splogin-user"

    def __init__(
            self,
            logger: Logger,
            sp_login_conf: Namespace | None = None
    ) -> None:
        """Ensure credential and browser availability for handler."""

        try:
            super().__init__(logger)
        except CredentialsException as exc:
            raise CredentialsException("No Spotify Credentials found") from exc

        if sp_login_conf is None:
            return  # only manage credentials without a given login_conf

        self.validate_browser_availability()

        try:
            self.spotify_login_button = sp_login_conf.spotify_login_button
            self.spotify_login_page = sp_login_conf.spotify_login_page
            self.spotify_username_field = sp_login_conf.spotify_username_field
            self.spotify_password_field = sp_login_conf.spotify_password_field
            self._validate_config()
        except AttributeError as exc:
            raise SpotifyLoginError(
                "Invalid config for Spotify Login"
            ) from exc

    def __call__(self) -> SpotifyAuthCookie:
        """Login to Spotify Web and return sp_dc and sp_key cookies."""
        try:
            with sync_playwright() as playwright:
                browser = playwright.firefox.launch()
                context = browser.new_context()
                page = context.new_page()
                page.goto(self.spotify_login_page)

                self.log.debug(
                    "filling credentials for %s",
                    self.credentials.username
                )
                page.fill(
                    "input#" + self.spotify_username_field,
                    self.credentials.username
                )
                page.fill(
                    "input#" + self.spotify_password_field,
                    self.credentials.password
                )

                self.log.debug("submitting login...")
                page.click("button#" + self.spotify_login_button)
                page.wait_for_load_state("networkidle")

                self.log.debug("extracting cookies")
                cookies = context.cookies()
                sp_dc = next(c for c in cookies if c["name"] == "sp_dc")
                sp_key = next(c for c in cookies if c["name"] == "sp_key")
                return SpotifyAuthCookie(sp_dc, sp_key)
        except Exception as exc:
            raise SpotifyLoginError("cannot extract cookies") from exc

    def _validate_config(self) -> None:
        """Raise AttributeError for a missing config value."""
        for attribute, value in vars(self).items():
            if attribute.startswith("spotify_") and value is None:
                raise AttributeError(f"sp_login_conf is missing '{attribute}'")

    @staticmethod
    def validate_browser_availability() -> None:
        """Raise BrowserUnavailableError if playwright launch fails."""
        with sync_playwright() as playwright:
            try:
                browser = playwright.firefox.launch()
                browser.close()
                return True
            except Exception as exc:  # pylint: disable=broad-exception-caught
                raise BrowserUnavailableError(
                    "playwright cannot launch browser"
                ) from exc


def main(args: Namespace) -> None:
    """Entrypoint for the splogin subcommand 'sp'."""
    log = get_logger(SpotifyWebLogin.SERVICE_NAME, args.log_level)
    log.debug(args)
