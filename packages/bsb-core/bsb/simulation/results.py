import contextlib
import traceback
import typing

from ..reporting import warn

if typing.TYPE_CHECKING:  # pragma: nocover
    import neo


class SimulationResult:
    def __init__(self, simulation, filename=None):
        from neo import Block, io

        tree = simulation.__tree__()
        with contextlib.suppress(KeyError):
            del tree["post_prepare"]
        if filename:
            self.filename = filename
            self.name = simulation.name
            io = io.NixIO(filename, mode="rw")
            io.write(Block(name=self.name, nix_name=self.name, config=tree))
            for i, nixblock in enumerate(io.nix_file.blocks):
                if self.name == nixblock.name:
                    self.block_id = i
            io.close()
        else:
            self.block = Block(
                name=simulation.name, nix_name=simulation.name, config=tree
            )

        self.recorders = []

    def add(self, recorder):
        self.recorders.append(recorder)

    def create_recorder(self, flush: typing.Callable[["neo.core.Segment"], None]):
        recorder = SimulationRecorder()
        recorder.flush = flush
        self.add(recorder)
        return recorder

    def flush(self):
        from neo import Segment, io

        segment = Segment()
        for recorder in self.recorders:
            try:
                recorder.flush(segment)
            except Exception:
                traceback.print_exc()
                warn("Recorder errored out!")
        if hasattr(self, "filename"):
            io = io.NixIO(self.filename, mode="rw")
            block = io.nix_file.blocks[self.block_id]
            io._write_segment(segment, block)
            io.close()
        else:
            self.block.segments.append(segment)

    def write(self, filename, mode):
        from neo import io

        if hasattr(self, "block"):
            io.NixIO(filename, mode=mode).write(self.block)


class SimulationRecorder:
    def flush(self, segment: "neo.core.Segment"):
        raise NotImplementedError("Recorders need to implement the `flush` function.")


__all__ = ["SimulationResult", "SimulationRecorder"]
