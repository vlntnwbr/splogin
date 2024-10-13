import getpass

import keyring
from keyring.credentials import Credential


DEFAULT_SERVICE_NAME = "splogin://spotify"


class CredentialsException(BaseException):
    pass


class CredentialManager:

    def __init__(self, service_name: str,  username: str | None = None):
        self.service_name = service_name
        self._credentials = self.validate(username)
        self.username = self._credentials.username
        self.password = self._credentials.password

    def validate(self, username: str) -> Credential:
        """Raises Exception if credentials for user are not found."""
        credentials = keyring.get_credential(self.service_name, username) 
        if credentials is None:
            raise CredentialsException(f"no password for {username}")
        return credentials

    def update(self, password: str | None) -> Credential:
        keyring.set_password(self.service_name, self.username, password)
    
    def delete(self) -> None:
        keyring.delete_password(self.service_name, self.username)
    
    @staticmethod
    def password_prompt() -> str:
        return getpass.getpass("Enter Password: ")
    
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
    print(service_name, "|", args)
    try:
        credentials = CredentialManager(service_name, args.username)
        if args.action == "del":
            credentials.delete()
            print(f"removed credentials for {credentials.username}")
        elif args.action == "set":
            credentials.update(args.password)
            print(f"updated credentials for {credentials.username}")
        else:
            print(f"found credentials for {credentials.username}")
    except CredentialsException as exc:
        if args.action in ("del", "get"):
            print(exc)
        elif args.action == "set":
            try:
                credentials = CredentialManager.add(
                    service_name, args.username, args.password
                )
                print(f"added credentials for {credentials.username}")
            except CredentialsException as exc:
                print(exc)
        else:
            print("no credentials found")
        

if __name__ == "__main__":
    main()