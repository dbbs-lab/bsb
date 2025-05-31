import os as _os

from arborize import file_schematic as _schema

from .models import expsyn as _expsyn
from .models import pas as _pas


def _mpath(path):
    return _os.path.join(_os.path.dirname(__file__), "morphologies", path)


def cell010():
    return _schema(_mpath("cell010.swc"))


def p75():
    with open(_mpath("P75.swc")) as _file:
        return _schema(_file)


def p75_pas():
    with open(_mpath("P75.swc")) as _file:
        return _schema(_file, definitions=_pas)


def p75_expsyn():
    with open(_mpath("P75.swc")) as _file:
        return _schema(_file, definitions=_expsyn)


def multitagged():
    return _schema(_mpath("multitagged.swc"))


def one_branch():
    return _schema(_mpath("one_branch.swc"))


def two_branch():
    return _schema(_mpath("two_branch.swc"))
