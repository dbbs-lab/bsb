from .._trace import t as _t

_t("bsb/services/_util.py: enter")
import importlib  # noqa: E402

from ..exceptions import DependencyError  # noqa: E402


class ErrorModule:
    def __init__(self, message):
        self._msg = message

    def __getattr__(self, attr):
        raise DependencyError(self._msg)


class MockModule:
    def __new__(cls, module):
        _t(f"bsb/services/_util.py: MockModule.__new__ pre  importlib.import_module({module!r})")
        try:
            instance = importlib.import_module(module)
            _t(f"bsb/services/_util.py: MockModule.__new__ post importlib.import_module({module!r}) -> real module")
        except ImportError as _e:
            _t(f"bsb/services/_util.py: MockModule.__new__ ImportError on {module!r}: {_e!r} -> mock")
            instance = super().__new__(cls)
            instance._mocked = True
        return instance
