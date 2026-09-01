"""
Provenance helpers shared by storage engines and the simulation result writer.

Exposes ``new_storage_id``, ``iso_now``, ``collect_plugin_manifest``,
``collect_host_info``, and ``build_root_metadata`` (the canonical assembler of
the root-level provenance bundle an engine writes on ``create()``), plus the
``encode_annotation``/``decode_annotation`` codec that gets structured metadata
into a file intact.
"""

import copy
import datetime
import functools
import getpass
import importlib.metadata
import json
import os
import platform
import socket
import uuid

import numpy as np

from .. import plugins
from ..reporting import warn

# Bump this when the layout of the provenance bundle written to storage roots
# or to ``.nio`` files changes in an incompatible way.
SCHEMA_VERSION = 1

# Plugin categories enumerated for the manifest. Keep in sync with the categories
# discovered by ``bsb.plugins.discover``.
_PLUGIN_CATEGORIES = (
    "storage.engines",
    "config.parsers",
    "config.templates",
    "simulation_backends",
    "commands",
    "options",
)


def _json_default(value):
    """Encode the numpy scalars and arrays that reach metadata from config values."""
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Can't encode '{value}' ({type(value)})")


def encode_annotation(value, what: str = "metadata") -> str:
    """
    Encode structured metadata as JSON for storage.

    Flat scalars survive a write on their own and should be stored as they are.
    Anything nested must not: ``neo``'s ``NixIO`` stores a dict annotation as
    nothing but its top-level keys, and HDF5 attributes have no nested form either,
    so a bundle written as a mapping reaches the file gutted of every value.

    Encoding failures degrade rather than taking a completed run down with them: a
    value that cannot be encoded warns and stores ``"null"``, because losing the
    metadata is a smaller loss than losing the results it describes.

    :param value: The metadata to encode.
    :param what: What is being encoded, named in the warning if it cannot be.
    :returns: A JSON string, or ``"null"`` if the value could not be encoded.
    """
    try:
        return json.dumps(value, default=_json_default)
    except TypeError as e:
        warn(f"Could not store the {what}: {e}")
        return "null"


def decode_annotation(value, default=None):
    """
    Read back what :func:`encode_annotation` wrote.

    A value that is not a JSON string is returned as-is, so metadata written before
    this codec existed reads back as whatever it was rather than raising.

    :param value: The stored value.
    :param default: What to return when there is nothing stored at all.
    :returns: The decoded metadata.
    """
    if value is None:
        return default
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def new_storage_id() -> str:
    """Return a fresh UUID4 string suitable for use as a ``storage_id``."""
    return str(uuid.uuid4())


def iso_now() -> str:
    """Return the current UTC time as an ISO 8601 string with seconds resolution."""
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def _safe_version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def collect_plugin_manifest() -> dict:
    """
    Walk every BSB plugin category and record ``{package, version}`` for each entry.

    The structure is ``{category: {entry_name: {"package": str, "version": str}}}``
    so a reader can answer "what plugins were installed when this artefact was
    written" without re-running discovery.
    """
    return copy.deepcopy(_discover_plugin_manifest())


@functools.lru_cache(maxsize=1)
def _discover_plugin_manifest() -> dict:
    manifest: dict[str, dict[str, dict[str, str | None]]] = {}
    for category in _PLUGIN_CATEGORIES:
        try:
            entries = plugins.discover(category)
        except Exception:
            # A broken plugin should not block writing provenance.
            manifest[category] = {}
            continue
        cat: dict[str, dict[str, str | None]] = {}
        for name, advert in entries.items():
            ep = getattr(advert, "_bsb_entry_point", None)
            package = getattr(getattr(ep, "dist", None), "name", None) if ep else None
            cat[name] = {
                "package": package,
                "version": _safe_version(package) if package else None,
            }
        manifest[category] = cat
    return manifest


def collect_host_info() -> dict:
    """Best-effort host fingerprint. None of the lookups are allowed to raise."""
    try:
        user = getpass.getuser()
    except Exception:
        user = None
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = None
    try:
        cwd = os.getcwd()
    except Exception:
        cwd = None
    return {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "hostname": hostname,
        "user": user,
        "cwd": cwd,
    }


def build_root_metadata(
    *,
    engine_name: str,
    engine_version: str | None,
    mpi_size: int,
) -> dict:
    """
    Build the root-level provenance bundle written by an engine on ``create()``.

    The returned dict is JSON-serialisable. Engines decide how to persist it
    (HDF5 attrs vs an FS ``metadata.json``).
    """
    return {
        "storage_id": new_storage_id(),
        "state_id": 0,
        "bsb_schema_version": SCHEMA_VERSION,
        "created_at": iso_now(),
        "bsb_core_version": _safe_version("bsb-core"),
        "engine_name": engine_name,
        "engine_version": engine_version,
        "plugins": collect_plugin_manifest(),
        "host": collect_host_info(),
        "mpi_size": int(mpi_size),
    }


__all__ = [
    "decode_annotation",
    "encode_annotation",
    "SCHEMA_VERSION",
    "build_root_metadata",
    "collect_host_info",
    "collect_plugin_manifest",
    "iso_now",
    "new_storage_id",
]
