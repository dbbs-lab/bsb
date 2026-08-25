import contextlib
import json
import shutil
import traceback
import typing
from datetime import datetime

import numpy as np

from ..reporting import warn

if typing.TYPE_CHECKING:  # pragma: nocover
    import neo


def _json_default(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Can't encode '{value}' ({type(value)})")


def _encode_simulation_config(tree):
    try:
        return json.dumps(tree, default=_json_default)
    except TypeError as e:
        warn(f"Could not store the simulation configuration with the results: {e}")
        return "null"


def read_simulation_config(block: "neo.core.Block") -> dict | None:
    """
    Read the configuration of the simulation that produced a block of results.

    :param block: Block of results, either taken from a
        :class:`~bsb.simulation.results.SimulationResult` or read back out of a
        results file.
    :type block: neo.core.Block
    :returns: The configuration tree of the simulation, or ``None`` if it could not be
        stored with the results.
    :rtype: dict | None
    :raises ValueError: If the block carries no readable configuration.
    """
    config = block.annotations.get("config")
    if not isinstance(config, str):
        raise ValueError(
            f"Block '{block.name}' carries no readable simulation configuration."
        )
    return json.loads(config)


class SimulationResult:
    def __init__(self, simulation, filename=None):
        from neo import Block

        tree = simulation.__tree__()
        with contextlib.suppress(KeyError):
            del tree["post_prepare"]
        self.recorders = []
        self.filename = filename
        # neo stores a dict annotation as nothing but its keys, so the configuration
        # is encoded as JSON, which reaches a results file intact.
        block = Block(name=simulation.name, config=_encode_simulation_config(tree))
        block.rec_datetime = datetime.now()
        if filename:
            from neo import io

            self._block = None
            with io.NixIO(filename, mode="rw") as out:
                run_index = sum(
                    1
                    for nb in out.nix_file.blocks
                    if nb.metadata
                    and "neo_name" in nb.metadata
                    and nb.metadata["neo_name"] == simulation.name
                )
                block.annotate(sim_name=simulation.name, run_index=run_index)
                out.write_block(block)
                self.block_key = block.annotations["nix_name"]
        else:
            self._block = block

    @property
    def block(self):
        if self._block is None:
            raise RuntimeError(
                f"Results were streamed to '{self.filename}'; read them back from "
                "the file, not from the result object."
            )
        return self._block

    def add(self, recorder):
        self.recorders.append(recorder)

    def create_recorder(self, flush: typing.Callable[["neo.core.Segment"], None]):
        recorder = SimulationRecorder()
        recorder.flush = flush
        self.add(recorder)
        return recorder

    def flush(self):
        from neo import Segment

        segment = Segment()
        for recorder in self.recorders:
            try:
                recorder.flush(segment)
            except Exception:
                traceback.print_exc()
                warn("Recorder errored out!")
        if self.filename:
            from neo import io

            with io.NixIO(self.filename, mode="rw") as out:
                out._write_segment(segment, out.nix_file.blocks[self.block_key])
        else:
            self._block.segments.append(segment)

    def write(self, filename, mode="ow"):
        if self.filename:
            shutil.copyfile(self.filename, filename)
        else:
            from neo import io

            io.NixIO(filename, mode=mode).write(self._block)


class SimulationRecorder:
    def flush(self, segment: "neo.core.Segment"):
        raise NotImplementedError("Recorders need to implement the `flush` function.")


__all__ = ["SimulationResult", "SimulationRecorder", "read_simulation_config"]
