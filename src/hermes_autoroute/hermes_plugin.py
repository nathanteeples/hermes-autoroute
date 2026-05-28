"""Entry-point plugin wrapper for pip-based Hermes discovery."""

from __future__ import annotations

from .cli import setup_argparse, run_from_args
from .commands import slash_status, start_background_router
from .provider import register_autoroute_provider


def _handle_cli(args):
    run_from_args(args)


def _setup_cli(subparser):
    setup_argparse(subparser)
    subparser.set_defaults(func=_handle_cli)


def register(ctx):
    register_autoroute_provider()
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
    ctx.register_hook("on_session_start", lambda **kwargs: start_background_router())
