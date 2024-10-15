"""Manager and Entrypoint for Spotify Credential Management."""

import getpass
from argparse import Namespace

import keyring
from keyring.credentials import Credential

from . import CredentialsException, get_logger, log_error


# TODO add exception handling for keyring


class CredentialManager:
    """Wrapper for python-keyring for Spotify Credential Management."""

    def __init__(self, service_name: str,  username: str | None = None):
        """Initialize the manager and ensure available credentials."""
        self.service_name = service_name
        self._credentials = self.validate(username)
        self.username = self._credentials.username
        self.password = self._credentials.password

    def validate(self, username: str | None) -> Credential:
        """Raise Exception if credentials for user are not found."""
        credentials = keyring.get_credential(self.service_name, username)
        if credentials is None:
            message = f"no password for {username}"
            if username is None:
                message = "no credentials found"
            raise CredentialsException(message)
        return credentials

    def update(self, password: str | None) -> None:
        """Update the user's password using keyring."""
        keyring.set_password(self.service_name, self.username, password)

    def delete(self) -> None:
        """Delete the user's Spotify Credentials from keyring."""
        keyring.delete_password(self.service_name, self.username)

    @staticmethod
    def password_prompt() -> str:
        """Get the password from user input."""
        return getpass.getpass("Enter Password: ").strip()

    @classmethod
    def add(cls, service_name: str, username: str, password: str | None):
        """Create a new set of credentials unless one already exists."""
        existing_user = keyring.get_credential(service_name, None)
        if existing_user is not None:
            raise CredentialsException(
                f"a user already exists: {existing_user.username}"
            )
        if password is None:
            password = cls.password_prompt()
        keyring.set_password(service_name, username, password)
        return cls(service_name, username)


def main(args: Namespace) -> None:
    """Entrypoint for splogin subcommand 'user'."""
    service_name = "splogin-user"
    log = get_logger(service_name, args.log_level)
    log.debug(args)
    try:
        auth = CredentialManager(service_name, args.username)
        if args.action == "del":
            auth.delete()
            log.warning("Removed Spotify credentials for %s", auth.username)
        elif args.action == "set":
            auth.update(args.password)
            log.info("Updated Spotify credentials for %s", auth.username)
        else:
            log.info("Found Spotify credentials for %s", auth.username)
    except CredentialsException as exc:
        if args.action == "set":
            try:
                auth = CredentialManager.add(
                    service_name, args.username, args.password
                )
                log.info("Added Spotify credentials for %s", auth.username)
            except CredentialsException as exc:
                log_error(log, exc)
        else:
            log.warning(exc)
    except Exception:
        log.critical("Unexpected Error", exc_info=True)


if __name__ == "__main__":
    main()
