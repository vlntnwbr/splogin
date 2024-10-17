"""Custom exceptions for splogin."""


class SPLoginException(Exception):
    """Common base class for all splogin exceptions."""

    def __str__(self) -> str:
        """Return the first exception argument as a representation."""
        return self.args[0]


class HomeAssistantApiError(SPLoginException):
    """Raised for errors during Home Assistant API calls."""


class BrowserUnavailableError(SPLoginException):
    """Raised when an error occurs during playwright browser launch."""


class CredentialError(SPLoginException):
    """Raised when credentials for a needed action are missing."""


class SpotifyLoginError(SPLoginException):
    """Raised for errors during automated Spotify Web login."""
