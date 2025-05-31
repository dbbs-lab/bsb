import contextlib
import typing

from .data import schematics

if typing.TYPE_CHECKING:
    from arborize.schematic import Schematic


class SchematicsFixture:
    p75: "Schematic"
    cell010: "Schematic"
    p75_pas: "Schematic"
    one_branch: "Schematic"
    two_branch: "Schematic"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tearDown(self):
        super().tearDown()
        for k, _ in vars(schematics).items():
            if not k.startswith("_"):
                with contextlib.suppress(Exception):
                    delattr(self, k)

    def __getattr__(self, attr):
        schemas = vars(schematics)
        if attr in schemas:
            schema = schemas[attr]()
            setattr(self, attr, schema)
            return schema
        else:
            return self.__getattribute__(attr)
