import contextlib
import importlib.metadata
import itertools
from inspect import isclass
from types import FunctionType

import docutils.parsers.rst.directives
from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import StringList
from sphinx.util.docutils import SphinxDirective

from bsb.config import get_config_attributes
from bsb.config._attrs import (
    ConfigurationDictAttribute,
    ConfigurationListAttribute,
)
from bsb.config._make import MISSING
from bsb.config.parsers import get_configuration_parser_classes
from bsb.config.types import class_

from .project import Project


def example_function():
    pass


_example_values = {
    bool: True,
    list: [],
    str: "example",
    int: 42,
    float: 3.14,
    FunctionType: "my_module.my_function",
    dict: {},
}


class ComponentIntro(Directive):
    has_content = False

    def run(self):
        # Use the state machine to generate a block quote for us and parse our text :)
        return self.state.block_quote(
            StringList(
                [
                    ":octicon:`light-bulb;1em;sd-text-info` New to components?"
                    + " Write your first one with :doc:`our guide </guides/components>`"
                ]
            ),
            self.content_offset,
        )


class AutoconfigNode(nodes.General, nodes.Element):
    pass


def visit_autoconfig_node(self, node):
    pass


def depart_autoconfig_node(self, node):
    pass


class AutoconfigDirective(SphinxDirective):
    required_arguments = 1
    has_content = False
    option_spec = {
        "no-imports": docutils.parsers.rst.directives.flag,
        "max-depth": docutils.parsers.rst.directives.positive_int,
    }

    def run(self):
        clsref = self.arguments[0]
        cls = class_()(clsref)
        max_depth = self.options.get("max-depth", 100)
        tree = self.guess_example(cls, max_depth)
        elem = AutoconfigNode()
        self.state.nested_parse(
            StringList(
                [
                    ".. tab-set-code::",
                    "",
                    "    .. code-block:: Python",
                    "",
                    *self.get_python_tab(
                        cls, tree, "no-imports" not in self.options, max_depth
                    ),
                    "",
                    *itertools.chain.from_iterable(
                        self.get_parser_lines(key, parser(), tree)
                        for key, parser in get_configuration_parser_classes().items()
                    ),
                ]
            ),
            self.content_offset,
            elem,
        )
        return [elem]

    def get_python_tab(self, cls, tree, imports, max_depth):
        lines = [
            *(
                f"        {imp}"
                for imp in self.get_import_lines(cls, max_depth if imports else 0)
            ),
            "",
            *(f"        {line}" for line in self.get_python_lines(cls, tree)),
        ]
        return self.collapse_empties(lines)

    def collapse_empties(self, lines, chars=None):
        if chars is None:
            chars = [("(", ")"), ("[", "]"), ("{", "}")]
        outlines = []
        skip = False
        for i in range(len(lines)):
            if skip:
                skip = False
                continue
            line1 = lines[i]
            if i == len(lines) - 1:
                outlines.append(line1)
                break
            line2 = lines[i + 1]
            for schar, echar in chars:
                if line1.endswith(schar) and line2.strip().startswith(echar):
                    outlines.append(line1 + f"{echar},")
                    skip = True
                    break
            else:
                outlines.append(line1)
        return outlines

    def guess_example(self, cls, deeper):
        if deeper == 0:
            return ...
        attrs = get_config_attributes(cls)
        tree = {
            attr.attr_name: self.guess_default(attr, deeper) for attr in attrs.values()
        }
        return tree

    def guess_default(self, attr, deeper):
        """
        Guess a default value/structure for the given attribute. Defaults are paired in
        tuples with functions that can unpack the tree value to their Python
        representation. The most basic "argument unpacker" exemplifies this, and turns
        the value ``x`` into ``f"{key}={repr(x)}"``.

        :param attr:
        :return:
        """
        type_ = self.get_attr_type(attr)

        # If the attribute is a node type, we have to guess recursively.
        is_public_untree = False
        if attr.is_node_type():
            # Node types that come from private modules shouldn't be promoted,
            # so instead we make use of the dictionary notation. Or, this autoconfig
            # has the "no-imports" option set, which disables the prepended import stmnt
            if "no-imports" in self.options or any(
                m.startswith("_") for m in type_.__module__.split(".")
            ):
                untree = self.private_untree(type_)
            else:
                untree = self.public_untree(type_)
                is_public_untree = True
            value = self.guess_example(type_, deeper - 1)
        else:
            untree = self.argument_untree
            value = self.guess_example_value(attr)
        # Configuration lists and dicts should be packed into a list/dict
        if isinstance(attr, ConfigurationListAttribute):
            untree = (
                self.list_untree(untree)
                if not is_public_untree
                else self.list_untree_public(untree)
            )
        elif isinstance(attr, ConfigurationDictAttribute):
            untree = self.dict_untree(untree)
        return untree, value

    def guess_example_value(self, attr):
        type_ = self.get_attr_type(attr)
        # The attribute may have a hinted example from the declaration `hint` kwarg,
        # or from the `__hint__` method of its type handler
        hint = attr.get_hint()
        if hint is not MISSING:
            example = hint
        else:
            # No hint, so check if the default is sensible
            default = attr.get_default()
            example = None
            if default is not None:
                example = default
            elif isclass(type_):
                # No default value, and likely a primitive was passed as type handler
                for parent_type, value in _example_values.items():
                    # Loop over some basic possible basic primitives
                    if issubclass(type_, parent_type):
                        example = value
                        break
            if example is None:
                # Try to have the type handler cast some primitive examples,
                # if no error is raised we assume it's a good example
                example = self.try_types(type_, *_example_values.values())
                # `str` is a kind of greedy type handler, so correct the casts
                if example == "[]":
                    example = []
                elif example == "{}":
                    example = {}
                elif example == "true":
                    example = True
                elif isinstance(attr, ConfigurationListAttribute):
                    example = [example] if example else []
        # Some values need to be cast back to a tree-form, so we create a shim
        # for the attribute descriptor to use as an instance.
        shim = type("AttrShim", (), {})()
        setattr(shim, f"_{attr.attr_name}", example)
        with contextlib.suppress(Exception):
            example = attr.tree(shim)
        # Hope we have a default value.
        return example

    def get_attr_type(self, attr):
        type_ = attr.get_type()
        type_ = str if type_ is None else type_
        return type_

    def try_types(self, type_, arg, *args):
        try:
            return type_(arg)
        except Exception:
            if args:
                return self.try_types(type_, *args)

    def get_python_lines(self, cls, tree):
        return [
            f"{cls.__name__}(",
            *(
                f"  {line}"
                for line in itertools.chain.from_iterable(
                    self.get_argument_lines(key, *value) for key, value in tree.items()
                )
            ),
            ")",
        ]

    def get_argument_lines(self, key, untree, value):
        return untree(key, value)

    def get_parser_lines(self, name, parser, tree):
        raw = self.raw_untree((None, tree))
        language = getattr(parser, "data_syntax", False) or name
        return [
            f"    .. code-block:: {language}",
            "",
            *(
                f"        {line}"
                for line in parser.generate(raw, pretty=True).split("\n")
            ),
            "",
        ]

    def raw_untree(self, tree):
        try:
            node_data = tree[1]
        except TypeError:
            # If the element wasn't packed as a tuple it's just a list/dict attr
            return tree
        list_repack = getattr(tree[0], "list_repack", False)
        dict_repack = getattr(tree[0], "dict_repack", False)
        if node_data is ...:
            if list_repack:
                return []
            else:
                return {}
        if dict_repack:
            node_data = {"name_of_the_thing": (None, node_data)}
        if list_repack:
            node_data = [(None, node_data)]
        if isinstance(node_data, dict):
            return {k: self.raw_untree(v) for k, v in node_data.items()}
        elif isinstance(node_data, list):
            return [self.raw_untree(v) for v in node_data]
        else:
            return node_data

    def public_untree(self, cls):
        def untree(key, value):
            if value is ...:
                lines = self.get_python_lines(cls, {})
            else:
                lines = self.get_python_lines(cls, value)
            lines[0] = f"{key}={lines[0]}"
            lines[-1] += ","
            return lines

        return untree

    def private_untree(self, cls):
        def untree(key, value):
            if value is ...:
                lines = self.get_python_lines(cls, {})
            else:
                lines = self.get_python_lines(cls, value)
            lines[0] = key + "={"
            for i in range(1, len(lines) - 1):
                line = lines[i]
                if "=" in line:
                    lp = line.split("=")
                    indent = len(lp[0]) - len(lp[0].lstrip())
                    lines[i] = f"{' ' * indent}'{lp[0].lstrip()}': " + "=".join(lp[1:])
            lines[-1] = "},"
            return lines

        return untree

    def dict_untree(self, inner_untree):
        def untree(key, value):
            lines = inner_untree(key, value)
            return lines

        untree.dict_repack = True
        return untree

    def list_untree(self, inner_untree):
        def untree(key, value):
            if value is ...:
                return [f"{key}=[", "],"]
            lines = inner_untree(key, value)
            # If lines come from private_untree
            # perform additional line editing
            if len(lines) > 1:
                lines[0] = lines[0].split("=")[0] + "=["
                lines.insert(1, "  {")
                lines[2:] = ["  " + line for line in lines[2:]]
                lines.append("],")
            return lines

        untree.list_repack = True
        return untree

    def list_untree_public(self, inner_untree):
        def untree(key, value):
            if value is ...:
                return [f"{key}=[", "],"]
            lines = inner_untree(key, value)
            split_ = lines[0].split("=")
            lines[0] = split_[0] + "=["
            lines.insert(1, split_[1])
            lines[1:] = ["  " + line for line in lines[1:]]
            lines.append("]")
            return lines

        untree.list_repack = True
        return untree

    def argument_untree(self, key, value):
        return [f"{key}={repr(value)},"]

    def get_imports(self, cls, deeper):
        imports = {}
        if not any(m.startswith("_") for m in cls.__module__.split(".")):
            imports.setdefault(cls.__module__, set()).add(cls.__name__)
        if deeper > 0:
            for attr in get_config_attributes(cls).values():
                if attr.is_node_type():
                    for k, v in self.get_imports(attr.get_type(), deeper - 1).items():
                        imports.setdefault(k, set()).update(v)

        return imports

    def get_import_lines(self, cls, depth):
        return [
            f"from {key} import {', '.join(value)}"
            for key, value in self.get_imports(cls, depth).items()
        ]


def resolve_type_aliases(app, env, node, contnode):
    if node["refdomain"] == "py" and node["reftype"] == "class":
        return app.env.get_domain("py").resolve_xref(
            env, node["refdoc"], app.builder, "data", node["reftarget"], node, contnode
        )


def setup(app):
    if "sphinx_design" not in app.extensions:
        from sphinx_design import setup as sphinx_design_setup

        sphinx_design_setup(app)

    app.add_node(
        AutoconfigNode,
        html=(visit_autoconfig_node, depart_autoconfig_node),
        latex=(visit_autoconfig_node, depart_autoconfig_node),
        text=(visit_autoconfig_node, depart_autoconfig_node),
    )
    app.add_directive("bsb_component_intro", ComponentIntro)
    app.add_directive("autoconfig", AutoconfigDirective)

    app.connect("missing-reference", resolve_type_aliases)

    return {
        "version": importlib.metadata.version("sphinxext-bsb"),
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }


__all__ = [
    "AutoconfigDirective",
    "AutoconfigNode",
    "ComponentIntro",
    "Project",
    "setup",
]
