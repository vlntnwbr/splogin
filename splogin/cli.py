from argparse import Action, ArgumentParser, Namespace
from os import getenv
from typing import Any, Sequence

from .credentials import main as splogin_user
from .splogin import main as splogin_main
from .hass import main as splogin_hass
from .validate import main as splogin_validate


class StoreMutuallyExclusiveFlags(Action):
    """A custom argparse action to store the flag of an argument."""

    FLAG_VARIABLE = "action"
    DEFAULT_FLAG = "DEFAULT_FLAG"

    def __call__(
        self,
        parser: ArgumentParser,
        namespace: Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None
    ) -> None:
        
        if getattr(namespace, self.FLAG_VARIABLE) == self.DEFAULT_FLAG:
            parser.error("options --{get, set, del} are mutually exclusive")
        setattr(namespace, self.FLAG_VARIABLE, option_string[2:])
        setattr(namespace, self.dest, values)


class CommandLineInterface:

    def __init__(self):
        
        self.argument_parser = ArgumentParser(
            "splogin",
            description="Automated Spotify Web login and cookie extraction"
        )
        self._add_main_options()
        self._add_common_options(splogin_main)
        
        self.subcommands = self.argument_parser.add_subparsers()
        self.add_user_command()
        self.add_hass_command()
        self.add_validate_command()
        
        self.args = self.argument_parser.parse_args()
        self.args.func(self.args)

    def _add_main_options(self) -> None:
        def add_env_var_arg(flag: str, message: str, var: str, default: Any):
            self.argument_parser.add_argument(
                flag,
                help=message,
                metavar="<value>",
                default=getenv("SPLOGIN_" + var, default)
        )

        add_env_var_arg(
            "--spotify-login-page",
            "URL for the Spotify Login Page",
            "SPOTIFY_LOGIN_PAGE",
            "https://accounts.spotify.com/de/login"
        )

        add_env_var_arg(
            "--spotify-login-button",
            "HTML element ID of login button on Spotify Login Page",
            "SPOTIFY_LOGIN_BUTTON",
            "login-button"
        )

        add_env_var_arg(
            "--spotify-password-field",
            "HTML element ID of password field on Spotify Login Page",
            "SPOTIFY_PASSWORD_FIELD",
            "login-password"
        )
        add_env_var_arg(
            "--spotify-username-field",
            "HTML element ID of username field on Spotify Login Page",
            "SPOTIFY_USERNAME_FIELD",
            "login-username"
        )
    
    def _add_subcommand(self, name: str, help_message: str) -> ArgumentParser:
        return self.subcommands.add_parser(
            name, description=help_message, help=help_message
        )
    
    def add_user_command(self) -> None:
        
        sub_parser = self._add_subcommand(
            "user", "Manage Spotify credentials using python-keyring"
        )

        add_action = lambda flag, message: sub_parser.add_argument(
            flag,
            dest="username",
            metavar="user",
            action=StoreMutuallyExclusiveFlags,
            help=message + " Spotify Email or username"
        )
        
        add_action("--get", "Find credential for")
        add_action("--set", "Set or update")
        add_action("--del", "Delete")
        sub_parser.set_defaults(action="DEFAULT_ACTION")

        sub_parser.add_argument(
            "--password",
            metavar="password",
            help="Password for set option. Use for non-interactive mode.",
        )

        self._add_common_options(splogin_user, sub_parser)
    
    def add_hass_command(self) -> None:
        sub_parser = self._add_subcommand(
            "hass", "Manage Home Assistant Token using python-keyring"
        )

        # TODO add argument token
        # TODO add argument for hass instance url via method
            # TODO add argument also to validate command)

        self._add_common_options(splogin_hass, sub_parser)
    
    def add_validate_command(self) -> None:
        
        sub_parser = self._add_subcommand(
            "validate", "Check if splogin is ready to run"
        )
        self._add_common_options(splogin_validate, sub_parser)
    
    def _add_common_options(
        self,
        handler: callable,
        parser: ArgumentParser | None = None
    ) -> None:
        
        if parser is None:
            parser = self.argument_parser
        parser.set_defaults(func=handler)
        
        parser.add_argument(
            "--log",
            help="set the logging level, default: WARNING",
            dest="log_level",
            type=lambda val: val.upper(),
            metavar="level",
            default="WARNING",
        )


if __name__ == "__main__":
    CommandLineInterface()