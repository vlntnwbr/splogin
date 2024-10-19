"""Application context for splogin."""

import os
import re
import sys

from argparse import ArgumentParser, Namespace, RawTextHelpFormatter
from pathlib import Path
from typing import Callable

from .utils import get_logger, log_error, playwright_install
from .utils.errors import (
    BrowserUnavailableError,
    CredentialError,
    HomeAssistantApiError,
    SPLoginException
)

from .utils.credentials import CredentialManager
from .spotify import SpotifyWebLogin
from .home_assistant import HomeAssistant


class CommandLineInterface:
    """Command Line Interface with env var loader for splogin."""

    def __init__(self):
        """Initialize cli. Load environment and run command handler."""
        # Create Argument Parser
        self.argument_parser = ArgumentParser(
            "splogin",
            description="Automated Spotify Web login and cookie extraction",
            formatter_class=RawTextHelpFormatter
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

        self.add_init_command()
        self.add_run_command()
        self.add_validate_command()
        self.add_credential_command(
            "hass",
            handler=HomeAssistant,
            username_help="Complete URL for Home Assistant instance."
        )
        self.add_credential_command(
            command="sp",
            handler=SpotifyWebLogin,
            username_help="Spotify Email or username"
        )
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

    @classmethod
    def entrypoint(cls) -> None:
        """Run the application without returning an instance."""
        cls()

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
        except Exception as exc:  # pylint: disable=broad-exception-caught
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

    def add_credential_command(
        self,
        command: str,
        handler: CredentialManager,
        username_help: str,
    ):
        """Add a subcommand parser for managing credentials."""
        env_var_flag = f"--{handler.SECRET_TYPE}"
        env_var = (
            f"{handler.SERVICE_ALIAS.replace(' ', '_').upper()}"
            f"_{handler.SECRET_TYPE.upper()}"
        )
        sub_parser = self._add_subcommand(
            command,
            message=f"manage {handler.SERVICE_ALIAS} {handler.SECRET_ALIAS}",
            epilog=(
                f"'splogin {command} rm' "
                f"removes existing {handler.SECRET_ALIAS}"
            ),
            max_help_position=len(env_var_flag) * 2 + 1
        )

        sub_parser.add_argument(
            handler.USER_ALIAS,
            help=username_help,
        )

        self._add_env_var_arg(
            env_var,
            env_var_flag,
            parser=sub_parser,
            dest="password",
            default=None,
            metavar=f"<{handler.SECRET_TYPE.lower()}>",
            help=(
                f"{handler.SERVICE_ALIAS} {handler.SECRET_TYPE}. "
                "Use for non-interactive mode."
            )
        )

        self._add_common_options(handler.cli, sub_parser)

    def add_init_command(self) -> None:
        """Add a command as an alias for 'validate --fix'."""
        def init_handler(args: Namespace) -> Callable[[Namespace], None]:
            """Set fix option in args and return validate handler."""
            setattr(args, "fix", True)
            setattr(args, "service_name", "splogin-init")
            return validate(args)

        sub_parser = self._add_subcommand(
            "init", "interactively add missing dependencies",
            "behaves identically to 'splogin validate --fix'\n"
        )
        self._add_common_options(init_handler, sub_parser)

    def add_run_command(self) -> None:
        """Add the parser for the 'run' command to the CLI."""
        sub_parser = self._add_subcommand(
            "run", "perform Spotify Web login and send data to Home Assistant",
            max_help_position=32
        )
        self._add_env_var_arg(
            "HOME_ASSISTANT_EVENT",
            "-e", "--event",
            parser=sub_parser,
            help="event to trigger in Home Assistant",
            metavar="<event>",
            default="new_spotcast_authentication"
        )
        self._add_env_var_arg(
            "SPOTIFY_LOGIN_PAGE",
            "--spotify-login-page",
            parser=sub_parser,
            help="full URL to the Spotify login page",
            metavar="<url>",
            default="https://accounts.spotify.com/login"
        )
        self._add_env_var_arg(
            "SPOTIFY_LOGIN_BUTTON",
            "--spotify-login-button",
            parser=sub_parser,
            help="id of submit button HTML element on --spotify-login-page",
            metavar="<id>",
            default="login-button"
        )
        self._add_env_var_arg(
            "SPOTIFY_LOGIN_USERNAME_FIELD",
            "--spotify-username-field",
            parser=sub_parser,
            help="id of username form HTML element on --spotify-login-page",
            metavar="<id>",
            default="login-username"
        )
        self._add_env_var_arg(
            "SPOTIFY_LOGIN_PASSWORD_FIELD",
            "--spotify-password-field",
            help="id of password field HTML element on --spotify-login-page",
            parser=sub_parser,
            metavar="<id>",
            default="login-password"
        )

        self._add_common_options(run, sub_parser)

    def add_validate_command(self) -> None:
        """Add the parser for the 'validate' subcommand to the CLI."""
        sub_parser = self._add_subcommand(
            "validate", "check if splogin is ready to run",
            max_help_position=40
        )
        sub_parser.add_argument(
            "--fix",
            action="store_true",
            help="set this to be prompted to fix every validation warning"
        )
        self._add_env_var_arg(
            "HOME_ASSISTANT_INSTANCE_URL",
            "--hass-instance-url",
            parser=sub_parser,
            help="Home Assistant instance url for non-interactive --fix",
            metavar="<url>"
        )
        self._add_env_var_arg(
            "HOME_ASSISTANT_TOKEN",
            "--hass-token",
            parser=sub_parser,
            help="Home Assistant Instance url for non-interactive --fix",
            metavar="<token>"
        )
        self._add_env_var_arg(
            "SPOTIFY_USER",
            "--spotify-user",
            parser=sub_parser,
            help="Spotify Email or username for non-interactive --fix",
            metavar="<user>"
        )
        self._add_env_var_arg(
            "SPOTIFY_PASSWORD",
            "--spotify-password",
            parser=sub_parser,
            help="Spotify password for non-interactive --fix",
            metavar="<password>"
        )
        self._add_common_options(validate, sub_parser)

    def _add_subcommand(
            self,
            name: str,
            message: str,
            epilog: str = "",
            max_help_position: int = 2
    ) -> ArgumentParser:
        """Create a parser used for a splogin subcommand."""
        return self.subcommands.add_parser(
            name,
            description=message,
            help=message,
            epilog=epilog,
            formatter_class=lambda prog: RawTextHelpFormatter(
                prog,
                max_help_position=max(24, max_help_position * 8 + 1),
            )
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
            metavar="<path>",
            type=Path,
            help=(
                "filepath pointing to an env file.\n"
                + " cli values take precedent even if set"
            )
        )

        self._add_env_var_arg(
            "LOG_LEVEL",
            "--log",
            parser=parser,
            help="set the logging level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            default="INFO",
            metavar="<level>",
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
        """Add an argument that can be set from environment."""
        default = add_argument_args.pop('default', None)
        help_msg = "\n".join((
            add_argument_args.pop("help", ""),
            " overwrites ${" + self.env_var_prefix + env_var + "}",
            f" default: {default}" if default is not None else "",
        ))
        (self.argument_parser if parser is None else parser).add_argument(
            *name_or_flags,
            default=os.getenv(self.env_var_prefix + env_var, default),
            help=help_msg,
            **add_argument_args
        )


def run(args: Namespace) -> None:
    """Entrypoint for subcommand 'splogin run'."""
    log = get_logger("splogin", args.log_level)
    log.debug(args)
    log.info("Fetching Spotify credentials and Home Assistant instance")
    try:
        spotify_web_login = SpotifyWebLogin(log, args)
        log.info("Using Spotify user %s", spotify_web_login)
        home_assistant = HomeAssistant(log)
        log.info("Using Home Assistant %s", home_assistant)
        spotify_login = spotify_web_login()
        log.info("Sending cookie data to Home Assistant")
        home_assistant.trigger_event(args.event, vars(spotify_login))
    except SPLoginException as exc:
        log_error(log, exc)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        log_error(log, exc, "An unexpected error occurred.")


def validate(args: Namespace):
    """Entrypoint for subcommand 'splogin validate'."""
    service_name = getattr(args, "service_name", "splogin-validate")
    log = get_logger(service_name, args.log_level)
    log.debug(args)

    log.info("Checking existence and validity of Home Assistant instance")
    try:
        hass = HomeAssistant(log)
        log.info("Using Home Assistant instance: %s", hass)
    except (CredentialError, HomeAssistantApiError) as exc:
        if isinstance(exc, CredentialError) and args.fix:
            log.warning("No instance found. Creating now...")
            instance = getattr(args, "hass_instance_url", None)
            if instance is None:
                instance = HomeAssistant.get_username_input("Instance URL")
            setattr(args, HomeAssistant.get_username_arg_name(), instance)
            setattr(args, "password", getattr(args, "hass_token", None))
            HomeAssistant.cli(args)
        else:
            log.warning(exc)

    log.info("Checking existence of credentials for Spotify Web login")
    try:
        spotify_login = SpotifyWebLogin(log)
        log.info("Using Spotify User: %s", spotify_login)
    except CredentialError:
        if args.fix:
            log.warning("No valid credentials found. Creating now...")
            username = getattr(args, "spotify_user", None)
            if username is None:
                username = SpotifyWebLogin.get_username_input(
                    "Spotify Email or username"
                )
            setattr(args, SpotifyWebLogin.get_username_arg_name(), username)
            setattr(args, "password", getattr(args, "spotify_password", None))
            SpotifyWebLogin.cli(args)
        else:
            log.warning("Spotify User Not Set")

    log.info("Checking Browser availability for Spotify Web Login")
    try:
        SpotifyWebLogin.validate_browser_availability()
        log.info("Browser for playwright is installed")
    except BrowserUnavailableError:
        log.warning("Found no usable Browser for playwright")
        if args.fix:
            try:
                playwright_install()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                log_error(log, exc, "Cannot install browser for playwright.")


if __name__ == "__main__":
    CommandLineInterface()
