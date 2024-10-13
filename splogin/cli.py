from argparse import Action, ArgumentParser, Namespace
from typing import Any, Sequence

from .credentials import main as splogin_user
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
        self._add_common_options(lambda args: print("splogin |", args))
        
        self.subcommands = self.argument_parser.add_subparsers(
            # help="available helper commands",
        )
        self.add_user_command()
        self.add_validate_command()
        
        self.args = self.argument_parser.parse_args()
        self.args.func(self.args)

    def add_user_command(self) -> None:
        
        message = "Manage Spotify credentials using python-keyring"
        sub_parser = self.subcommands.add_parser(
            "user", description=message, help=message
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
    
    def add_validate_command(self) -> None:
        
        message = "Check if all requirements are met for running splogin."
        sub_parser = self.subcommands.add_parser(
            "validate", description=message, help=message            
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