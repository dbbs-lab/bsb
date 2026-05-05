# fmt: off
# isort: off
from .._trace import t as _t  # noqa: E402

_t("bsb/cli/__init__.py: enter")
_t("bsb/cli/__init__.py: pre  import builtins")
import builtins  # noqa: E402
_t("bsb/cli/__init__.py: post import builtins")
_t("bsb/cli/__init__.py: pre  import inspect")
import inspect  # noqa: E402
_t("bsb/cli/__init__.py: post import inspect")
_t("bsb/cli/__init__.py: pre  import json")
import json  # noqa: E402
_t("bsb/cli/__init__.py: post import json")
_t("bsb/cli/__init__.py: pre  import sys")
import sys  # noqa: E402
_t("bsb/cli/__init__.py: post import sys")

_t("bsb/cli/__init__.py: pre  from .._contexts import ...")
from .._contexts import get_cli_context, reset_cli_context  # noqa: E402
_t("bsb/cli/__init__.py: post from .._contexts import ...")
_t("bsb/cli/__init__.py: pre  from ..exceptions import CommandError, DryrunError")
from ..exceptions import CommandError, DryrunError  # noqa: E402
_t("bsb/cli/__init__.py: post from ..exceptions import CommandError, DryrunError")
_t("bsb/cli/__init__.py: pre  from bsb_otel import get_bsb_tracer")
from bsb_otel import get_bsb_tracer  # noqa: E402
_t("bsb/cli/__init__.py: post from bsb_otel import get_bsb_tracer")
_t("bsb/cli/__init__.py: pre  from .commands import load_root_command")
from .commands import load_root_command  # noqa: E402
_t("bsb/cli/__init__.py: post from .commands import load_root_command")
# fmt: on
# isort: on


def handle_cli():
    _t("bsb/cli/__init__.py: handle_cli() enter")
    handle_command(sys.argv[1:], exit=True)
    _t("bsb/cli/__init__.py: handle_cli() return")


def handle_command(command, dryrun=False, exit=False):
    _t(f"bsb/cli/__init__.py: handle_command() enter command={command!r}")
    reset_cli_context()
    _t("bsb/cli/__init__.py: handle_command pre get_cli_context")
    context = get_cli_context()
    _t("bsb/cli/__init__.py: handle_command pre load_root_command")
    root_command = load_root_command()
    _t("bsb/cli/__init__.py: handle_command pre get_parser")
    parser = root_command.get_parser(context)
    _t("bsb/cli/__init__.py: handle_command pre parse_args")
    try:
        namespace = parser.parse_args(command)
    except CommandError as e:
        if exit:
            print(e)
            builtins.exit(1)
        else:
            raise
    _t("bsb/cli/__init__.py: handle_command post parse_args")
    if not dryrun:
        for action in namespace.internal_action_list or ():
            action(namespace)
    if not dryrun or _can_dryrun(namespace.handler, namespace):
        _t("bsb/cli/__init__.py: handle_command pre tracer.trace")
        with get_bsb_tracer("bsb-core").trace(
            "cli",
            attributes={
                "bsb.cli_command": command,
                "bsb.context": json.dumps(
                    {
                        opt.name: str(opt.get())
                        for opt in namespace._context.options.values()
                    }
                ),
            },
        ):
            _t(f"bsb/cli/__init__.py: handle_command pre handler {namespace.handler}")
            namespace.handler(namespace, dryrun=dryrun)
            _t("bsb/cli/__init__.py: handle_command post handler")
    else:  # pragma: nocover
        raise DryrunError(f"`{namespace.handler.__name__}` doesn't support dryruns.")
    _t("bsb/cli/__init__.py: handle_command return")
    return context


def _can_dryrun(handler, namespace):
    try:
        return bool(inspect.signature(handler).bind(namespace, dryrun=True))
    except TypeError:
        return False


__all__ = ["handle_cli", "handle_command"]
