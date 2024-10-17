"""Handler and entrypoint for automated Spotify Web login."""

from argparse import Namespace
from dataclasses import dataclass, fields
from logging import Logger
from typing import Any, Generator, TypeVar

from playwright.sync_api import sync_playwright

from splogin.utils.errors import SpotifyLoginError

from .utils.errors import BrowserUnavailableError, CredentialError

from .utils.credentials import CredentialManager

CookieValue = TypeVar("CookieValue", bool, float, str)


@dataclass(frozen=True, repr=True, )
class SpotifyAuthCookie:
    """Container for Spotify cookie using its fields as cookie names."""

    sp_dc: str
    sp_key: str

    @classmethod
    def iter_cookie_names(cls) -> Generator[str, Any, None]:
        """Iterate over all cookies whose values must be extracted."""
        for cookie in fields(cls):
            yield cookie.name

    @classmethod
    def from_playwright_cookies(cls, cookies: list[dict[str, CookieValue]]):
        """Extract values from playwright Spotify Login cookies."""
        return cls(**{
            cookie_name: cls.get_cookie_value_by_name(cookie_name, cookies)
            for cookie_name in cls.iter_cookie_names()
        })

    @staticmethod
    def get_cookie_value_by_name(
        name: str,
        cookies: list[dict[str, CookieValue]]
    ) -> CookieValue:
        """Return value for the cookie with the given name"""
        return next(c["value"] for c in cookies if c["name"] == name)


class SpotifyWebLogin(CredentialManager):
    """Handler for automated Spotify Web login and cookie extraction."""

    SERVICE_NAME = "splogin-user"
    SERVICE_ALIAS = "Spotify"
    SECRET_ALIAS = "credentials"  # nosec
    SECRET_TYPE = "password"  # nosec
    USER_ALIAS = "user"

    def __init__(
            self,
            logger: Logger,
            sp_login_conf: Namespace | None = None
    ) -> None:
        """Ensure credential and browser availability for handler."""
        try:
            super().__init__(logger)
        except CredentialError as exc:
            raise CredentialError("No Spotify Credentials found") from exc

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
                return SpotifyAuthCookie.from_playwright_cookies(cookies)
        except Exception as exc:
            raise SpotifyLoginError(
                f"Unable to log into spotify as {self}"
            ) from exc

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
                    "Error during playwright browser launch"
                ) from exc
