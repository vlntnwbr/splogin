from argparse import Action, ArgumentParser, ArgumentTypeError, Namespace
from typing import Any, Sequence

from .credentials import main as user_management

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
        self.subcommands = self.argument_parser.add_subparsers(
            help="available helper commands",
        )
        self.add_handler(lambda args: print("splogin |", args))
        self.add_user_command()
        
        self.args = self.argument_parser.parse_args()
        self.args.func(self.args)

    def add_user_command(self) -> None:
        
        message = "fetch, update or remove Spotify credentials from keyring"
        sub_parser = self.subcommands.add_parser(
            "user",
            description=message,
            help=message
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
            help="Password for set option. Use for non-interactive mode.",
        )

        self.add_handler(user_management, sub_parser)
    
    def add_handler(
        self,
        handler: callable,
        parser: ArgumentParser | None = None
    ) -> None:
        if parser is None:
            parser = self.argument_parser
        parser.set_defaults(func=handler)


if __name__ == "__main__":
    CommandLineInterface()