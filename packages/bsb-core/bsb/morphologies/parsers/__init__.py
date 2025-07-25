from __future__ import annotations

from os import PathLike

from .parser import MorphologyParser


def parse_morphology_content(content: str | bytes, parser="bsb", **kwargs):
    return MorphologyParser(parser=parser, **kwargs).parse_content(content)


def parse_morphology_file(file: str | PathLike, parser="bsb", **kwargs):
    return MorphologyParser(parser=parser, **kwargs).parse(file)


__all__ = ["parse_morphology_content", "parse_morphology_file"]
