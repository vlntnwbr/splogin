import getpass

import keyring
from keyring.credentials import Credential

from . import CredentialsException, get_logger


class CredentialManager:

    def __init__(self, service_name: str,  username: str | None = None):
        self.service_name = service_name
        self._credentials = self.validate(username)
        self.username = self._credentials.username
        self.password = self._credentials.password

    def validate(self, username: str | None) -> Credential:
        """Raises Exception if credentials for user are not found."""
        credentials = keyring.get_credential(self.service_name, username) 
        if credentials is None:
            message = f"no password for {username}"
            if username is None:
                message = "no credentials found"
            raise CredentialsException(message)
        return credentials

    def update(self, password: str | None) -> Credential:
        keyring.set_password(self.service_name, self.username, password)
    
    def delete(self) -> None:
        keyring.delete_password(self.service_name, self.username)
    
    @staticmethod
    def password_prompt() -> str:
        return getpass.getpass("Enter Password: ").strip()
    
    @classmethod
    def add(cls, service_name: str, username: str, password: str | None):
        existing_user = keyring.get_credential(service_name, None)
        if existing_user is not None:
            raise CredentialsException(
                f"a user already exists: {existing_user.username}"
            )
        if password is None:
            password = cls.password_prompt()
        keyring.set_password(service_name, username, password)
        return cls(service_name, username)

    
def main(args) -> None:
    service_name = "splogin-user"
    log = get_logger(service_name, args.log_level)
    log.debug(args)
    try:
        credentials = CredentialManager(service_name, args.username)
        if args.action == "del":
            credentials.delete()
            log.warning("removed credentials for %s", credentials.username)
        elif args.action == "set":
            credentials.update(args.password)
            log.info("updated credentials for %s", credentials.username)
        else:
            log.info("found credentials for %s", credentials.username)
    except CredentialsException as exc:
        if args.action == "set":
            try:
                credentials = CredentialManager.add(
                    service_name, args.username, args.password
                )
                log.info("added credentials for %s", credentials.username)
            except CredentialsException as exc:
                log.error("could not add user: %s", exc)
                log.debug(exc, exc_info=True)
        else:
            log.warning(exc)
    except Exception as exc:
        log.critical("Unexpected Error", exc_info=True)
        

if __name__ == "__main__":
    main()