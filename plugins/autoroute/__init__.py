"""Hermes general plugin for Autoroute commands and diagnostics."""

from hermes_autoroute.cli import setup_argparse, run_from_args
from hermes_autoroute.commands import slash_status, start_background_router


def _handle_cli(args):
    run_from_args(args)


def _setup_cli(subparser):
    setup_argparse(subparser)
    subparser.set_defaults(func=_handle_cli)


def _on_session_start(**kwargs):
    start_background_router()
    return None


def register(ctx):
    ctx.register_cli_command(
        name="autoroute",
        help="Manage intelligent model routing",
        setup_fn=_setup_cli,
        handler_fn=_handle_cli,
    )
    ctx.register_command(
        "autoroute",
        handler=slash_status,
        description="Show Autoroute status and latest model decision",
    )
    ctx.register_hook("on_session_start", _on_session_start)

