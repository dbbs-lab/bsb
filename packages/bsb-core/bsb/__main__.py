# fmt: off
# isort: off
from ._trace import t as _t  # noqa: E402

_t("bsb/__main__.py: enter")
_t("bsb/__main__.py: pre  from . import cli")
from . import cli  # noqa: E402
_t("bsb/__main__.py: post from . import cli")

_t("bsb/__main__.py: pre  cli.handle_cli()")
cli.handle_cli()
_t("bsb/__main__.py: post cli.handle_cli()")
# fmt: on
# isort: on
