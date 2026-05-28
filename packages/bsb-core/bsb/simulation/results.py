import contextlib
import shutil
import traceback
import typing
from datetime import datetime

from ..reporting import warn

if typing.TYPE_CHECKING:  # pragma: nocover
    import neo


class SimulationResult:
    def __init__(self, simulation, filename=None):
        from neo import Block

        tree = simulation.__tree__()
        with contextlib.suppress(KeyError):
            del tree["post_prepare"]
        self.recorders = []
        self.filename = filename
        block = Block(name=simulation.name, config=tree)
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
    def block(self) -> "neo.Block":
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


__all__ = ["SimulationResult", "SimulationRecorder"]
