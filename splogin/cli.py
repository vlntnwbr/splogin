"""Application context for splogin."""

import os
import re
import sys

from argparse import Action, ArgumentParser, Namespace
from pathlib import Path
from typing import Any, Sequence, Callable


from .credentials import main as splogin_user
from .splogin import main as splogin_run
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
        """Validate option exclusivity, store flag and given value."""
        if getattr(namespace, self.FLAG_VARIABLE) == self.DEFAULT_FLAG:
            parser.error("options --{get, set, del} are mutually exclusive")
        setattr(namespace, self.FLAG_VARIABLE, option_string[2:])
        setattr(namespace, self.dest, values)


class CommandLineInterface:
    """Command Line Interface with env var loader for splogin."""

    def __init__(self):
        """Initialize cli. Load environment and run command handler."""
        # Create Argument Parser
        self.argument_parser = ArgumentParser(
            "splogin",
            description="Automated Spotify Web login and cookie extraction"
        )

        # Load .env
        self.env_var_prefix = "SPLOGIN_"
        self.env_file_flag = "--env-file"
        if (env_file := self.get_env_file()) is not None:
            self.load_env(env_file)

        # Initiate Subcommands
        self.subcommands = self.argument_parser.add_subparsers(
            description="these commands support all options listed above",
        )
        self.add_user_command()
        self.add_run_command()
        self.add_hass_command()
        self.add_validate_command()
        self._add_common_options()

        # Determine Command Handler and run it
        args = self.argument_parser.parse_args()
        run_command_handler: Callable[[Namespace], None] | None = getattr(
            args, "func", None
        )
        if run_command_handler is not None:
            delattr(args, "func")
            run_command_handler(args)
        else:
            self.argument_parser.print_help()

    def add_hass_command(self) -> None:
        """Add the parser for the 'hass' subcommand to the CLI."""
        sub_parser = self._add_subcommand(
            "hass", "create Home Assistant instance using python-keyring"
        )

        sub_parser.add_argument(
            "instance_url",
            help="URL (with scheme & port) for Home Assistance instance",
            metavar="instance-url",
        )

        self._add_env_var_arg(
            "HASS_TOKEN",
            "--token",
            parser=sub_parser,
            help="Home Assistant API token. Use for non-interactive mode.",
            default=None,
            metavar="TOKEN",
        )

        self._add_common_options(splogin_hass, sub_parser)

    def add_run_command(self) -> None:
        """Add the parser for the 'run' subcommand to the CLI."""
        sub_parser = self._add_subcommand(
            "run", "perform Spotify login trigger Home Assistant event"
        )

        self._add_env_var_arg(
            "SPOTIFY_LOGIN_PAGE",
            "--spotify-login-page",
            parser=sub_parser,
            help="URL for the Spotify Login Page",
            default="https://accounts.spotify.com/de/login",
            metavar="URL",
        )

        self._add_env_var_arg(
            "SPOTIFY_LOGIN_BUTTON",
            "--spotify-login-button",
            parser=sub_parser,
            help="HTML element ID of login button on Spotify Login Page",
            default="login-button",
            metavar="ELEMENT_ID",
        )

        self._add_env_var_arg(
            "SPOTIFY_PASSWORD_FIELD",
            "--spotify-password-field",
            parser=sub_parser,
            help="HTML element ID of password field on Spotify Login Page",
            default="login-password",
            metavar="ELEMENT_ID",
        )

        self._add_env_var_arg(
            "SPOTIFY_USERNAME_FIELD",
            "--spotify-username-field",
            parser=sub_parser,
            help="HTML element ID of username field on Spotify Login Page",
            default="login-username",
            metavar="ELEMENT_ID",
        )

        self._add_common_options(splogin_run, parser=sub_parser)

    def add_user_command(self) -> None:
        """Add the parser for the 'user' subcommand to the CLI."""
        sub_parser = self._add_subcommand(
            "user", "manage Spotify credentials using python-keyring"
        )

        def add_action(flag: str, message: str):
            sub_parser.add_argument(
                flag,
                dest="username",
                metavar="USER",
                action=StoreMutuallyExclusiveFlags,
                help=message + " Spotify Email or username"
            )

        add_action("--get", "find credential for")
        add_action("--set", "set or update")
        add_action("--del", "delete")
        sub_parser.set_defaults(action="DEFAULT_ACTION")

        sub_parser.add_argument(
            "--password",
            metavar="PASSWORD",
            help="password for set option. Use for non-interactive mode.",
        )

        self._add_common_options(splogin_user, sub_parser)

    def add_validate_command(self) -> None:
        """Add the parser for the 'validate' subcommand to the CLI."""
        sub_parser = self._add_subcommand(
            "validate", "check if splogin is ready to run"
        )
        self._add_common_options(splogin_validate, sub_parser)

    def _add_subcommand(self, name: str, help_message: str) -> ArgumentParser:
        """Create a parser used for a splogin subcommand."""
        return self.subcommands.add_parser(
            name, description=help_message, help=help_message
        )

    def _add_common_options(
        self,
        handler: Callable[[Namespace], None] | None = None,
        parser: ArgumentParser | None = None
    ) -> None:
        """Add common command options to the given or main parser."""
        if parser is None:
            parser = self.argument_parser
        parser.set_defaults(func=handler)

        parser.add_argument(
            self.env_file_flag,
            help="filepath pointing to an env file. Default: .env",
            metavar="PATH",
            type=Path
        )

        self._add_env_var_arg(
            "LOG_LEVEL",
            "--log",
            parser=parser,
            help="set the logging level, default: INFO",
            default="INFO",
            metavar="LEVEL",
            dest="log_level",
            type=lambda val: val.upper()
        )

    def _add_env_var_arg(
        self,
        env_var: str,
        *name_or_flags: str,
        parser: ArgumentParser | None = None,
        **add_argument_args
    ) -> None:
        """Add an optional argument that can be set from environment."""
        default = add_argument_args.pop('default', None)
        (self.argument_parser if parser is None else parser).add_argument(
            *name_or_flags,
            default=os.getenv(self.env_var_prefix + env_var, default),
            **add_argument_args
        )

    def get_env_file(self) -> Path | None:
        """Return the filepath for the --env-file argument."""
        try:
            return Path(sys.argv[sys.argv.index(self.env_file_flag) + 1])
        except IndexError:
            self.argument_parser.error(
                f"argument {self.env_file_flag}: expected one argument"
            )
        except ValueError:
            pass
        return None

    def load_env(self, env_file: Path) -> None:
        """Load environment variables from given file."""
        try:
            lines = (
                line.strip() for line in
                env_file.absolute().read_text().splitlines()
                if line.strip() and not line.startswith("#")
            )
        except BaseException as exc:  # pylint: disable=broad-exception-caught
            self.argument_parser.error(
                f"argument {self.env_file_flag}: "
                f"error loading '{env_file}': "
                f"{exc}"
            )
        expansion_pattern = r"(\${(.*?)})"  # matches ${ENV_VAR_TO_EXPAND}

        for line in lines:
            env_var, env_file_value = line.split("=", 1)
            must_expand_query = re.search(expansion_pattern, env_file_value)

            env_var_value = re.sub(
                expansion_pattern,
                os.getenv(
                    must_expand_query.group(2),  # == 'ENV_VAR_TO_EXPAND'
                    must_expand_query.group(1)  # == '${ENV_VAR_TO_EXPAND}'
                ),
                must_expand_query.string
            ) if must_expand_query is not None else env_file_value

            os.environ[env_var.strip()] = env_var_value.strip()


if __name__ == "__main__":
    CommandLineInterface()
