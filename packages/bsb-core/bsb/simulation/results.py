import contextlib
import dataclasses
import traceback
import typing
import uuid

from ..reporting import warn
from ..storage.provenance import (
    SCHEMA_VERSION,
    collect_host_info,
    collect_plugin_manifest,
    iso_now,
)

if typing.TYPE_CHECKING:  # pragma: nocover
    import neo


class SimulationResult:
    def __init__(self, simulation):
        from neo import Block

        tree = simulation.__tree__()
        with contextlib.suppress(KeyError):
            del tree["post_prepare"]
        self.block = Block(name=simulation.name, config=tree)
        self.recorders = []
        self.simulation = simulation
        self.simulation_id = str(uuid.uuid4())
        self._segment_id = None
        scaffold = getattr(simulation, "scaffold", None)
        self._provenance = {
            "schema_version": SCHEMA_VERSION,
            "simulation_id": self.simulation_id,
            "simulation_name": simulation.name,
            "started_at": None,
            "finished_at": None,
            "wall_seconds": None,
            "seed": getattr(simulation, "seed", None),
            "duration_ms": getattr(simulation, "duration", None),
            "resolution_ms": getattr(simulation, "resolution", None),
            "scaffold": _scaffold_provenance(scaffold),
            "plugins": collect_plugin_manifest(),
            "simulator": {"name": None, "version": None, "extra": {}},
            "host": collect_host_info(),
            "mpi_size": _mpi_size(scaffold),
        }
        self.block.annotate(bsb_provenance=self._provenance)

    @property
    def spiketrains(self):
        return self.block.segments[0].spiketrains

    @property
    def analogsignals(self):
        return self.block.segments[0].analogsignals

    @property
    def segment_id(self) -> str | None:
        """UUID of the segment currently being flushed (set during ``flush``)."""
        return self._segment_id

    def set_simulator(self, name: str, version: str | None = None, **extra) -> None:
        """Adapters call this in ``prepare`` so simulator metadata lands on the Block."""
        self._provenance["simulator"] = {
            "name": name,
            "version": version,
            "extra": dict(extra),
        }

    def mark_started(self, started_at: str | None = None) -> None:
        self._provenance["started_at"] = started_at or iso_now()

    def mark_finished(
        self, *, finished_at: str | None = None, wall_seconds: float | None = None
    ) -> None:
        self._provenance["finished_at"] = finished_at or iso_now()
        if wall_seconds is not None:
            self._provenance["wall_seconds"] = float(wall_seconds)

    def add(self, recorder):
        self.recorders.append(recorder)

    def create_recorder(
        self,
        flush: typing.Callable[["neo.core.Segment"], None],
        *,
        device=None,
        meta: dict | None = None,
    ):
        """
        Register ``flush`` as a recorder. Pass ``device`` to link the recorder
        back to it (sets ``recorder.device_name``) and ``meta`` to expose
        recorder-level metadata queryable at runtime via ``recorder.meta(...)``.
        """
        recorder = SimulationRecorder(device=device, meta=meta)
        recorder.flush = flush
        self.add(recorder)
        return recorder

    def flush(self):
        from neo import Segment

        segment = Segment()
        self._segment_id = str(uuid.uuid4())
        sim = self.simulation
        segment.annotate(
            segment_id=self._segment_id,
            checkpoint_index=len(self.block.segments),
            t_start_ms=0.0,
            t_stop_ms=float(getattr(sim, "duration", 0.0) or 0.0),
            simulator_state={},
        )
        self.block.segments.append(segment)
        for recorder in self.recorders:
            try:
                recorder.flush(segment)
            except Exception:
                traceback.print_exc()
                warn("Recorder errored out!")
        self._segment_id = None

    def write(self, filename, mode):
        from neo import io

        io.NixIO(filename, mode=mode).write(self.block)

    # ---- convenience constructors for the standard annotation contract ------

    def spike_train(
        self,
        *,
        times,
        ps_name: str,
        cell_id: int,
        cell_model,
        device,
        t_stop,
        units: str = "ms",
        recording_kind: str = "cell",
        **fields,
    ):
        """
        Build a :class:`neo.SpikeTrain` carrying the baseline ``bsb_*``
        annotations plus the ``"cell"``-target fields. See :meth:`analog_signal`
        for the annotation layering and how ``fields`` extends it.

        Convenience only: BSB does not validate or require recorders to use it.
        Recorders are free to emit any Neo objects they want, in any quantity.
        """
        from neo import SpikeTrain

        return SpikeTrain(
            times=times,
            units=units,
            t_stop=t_stop,
            **_bsb_annotations(
                self,
                device=device,
                recording_kind=recording_kind,
                ps_name=ps_name,
                cell_id=cell_id,
                cell_model=cell_model,
                fields=fields,
            ),
        )

    def analog_signal(
        self,
        *,
        data,
        units,
        sampling_period,
        name: str,
        ps_name: str,
        cell_id: int,
        cell_model,
        device,
        recording_kind: str = "cell",
        **fields,
    ):
        """
        Build a :class:`neo.AnalogSignal` carrying the layered ``bsb_*``
        annotations.

        The annotations come in two layers, all as flat sibling keys. The
        **baseline** identifies what is doing the recording and ties the object
        back to its run: ``bsb_device_name``, ``bsb_device_kind``,
        ``bsb_recording_kind``, ``bsb_simulation_id``, ``bsb_segment_id``. The
        **recording-kind** layer, selected by ``recording_kind``, declares what
        is being recorded; this helper fills the ``"cell"`` anchor
        (``bsb_ps_name``, ``bsb_cell_id``, ``bsb_cell_model``) shared by the
        cell, compartment and synapse kinds.

        Neo's native fields carry the recorded quantity: ``name`` is the label
        (e.g. ``"V_m"``, ``"I_syn"``) and ``units`` the dimension.

        Any extra ``fields`` are namespaced as first-class ``bsb_<key>``
        annotations alongside the baseline, so a kind that records a compartment
        passes ``section=..., arc=...`` and gets ``bsb_section`` / ``bsb_arc``.
        """
        from neo import AnalogSignal

        return AnalogSignal(
            data,
            units=units,
            sampling_period=sampling_period,
            name=name,
            **_bsb_annotations(
                self,
                device=device,
                recording_kind=recording_kind,
                ps_name=ps_name,
                cell_id=cell_id,
                cell_model=cell_model,
                fields=fields,
            ),
        )


def _bsb_annotations(
    result, *, device, recording_kind, ps_name, cell_id, cell_model, fields
):
    """
    Compose the layered ``bsb_*`` annotation dict: a baseline every recorder
    shares, the ``"cell"`` anchor that the cell/compartment/synapse recording
    kinds build on, and any per-kind ``fields`` namespaced as flat ``bsb_<key>``
    keys.
    """
    device_name = getattr(device, "name", device)
    device_cls = type(device) if not isinstance(device, type) else device
    device_kind = getattr(device_cls, "classmap_entry", device_cls.__name__)
    ann = {
        # Baseline: shared by every recorder regardless of recording kind.
        "bsb_device_name": device_name,
        "bsb_device_kind": device_kind,
        "bsb_recording_kind": recording_kind,
        "bsb_simulation_id": result.simulation_id,
        "bsb_segment_id": result.segment_id,
        # Cell anchor: the cell/compartment/synapse kinds.
        "bsb_ps_name": ps_name,
        "bsb_cell_id": int(cell_id),
        "bsb_cell_model": getattr(cell_model, "name", cell_model),
    }
    # Target-kind extension: flat siblings, namespaced under bsb_.
    ann.update({f"bsb_{key}": value for key, value in fields.items()})
    return ann


def _scaffold_provenance(scaffold) -> dict:
    if scaffold is None:
        return {"storage_id": None, "state_id": None, "root": None}
    try:
        return {
            "storage_id": scaffold.storage_id,
            "state_id": scaffold.state_id,
            "root": str(scaffold.storage.root),
        }
    except Exception:
        return {"storage_id": None, "state_id": None, "root": None}


def _mpi_size(scaffold) -> int:
    if scaffold is None:
        return 1
    try:
        return int(scaffold._comm.get_size())
    except Exception:
        return 1


class SimulationRecorder:
    """
    A recorder appends Neo objects to a segment on each ``flush``. It is also
    inspectable at runtime, before anything is written to file: ``device_name``
    links it back to the device that created it, and ``meta`` exposes
    recorder-level metadata. This lets a controller (e.g. an LFP probe) find the
    recorders of the devices it manages during a flush and query their metadata,
    such as ``recorder.meta("lfp_source_geometry")``.
    """

    def __init__(self, device=None, meta: dict | None = None):
        self.device_name = getattr(device, "name", device)
        self._meta = dict(meta or {})

    def flush(self, segment: "neo.core.Segment"):
        raise NotImplementedError("Recorders need to implement the `flush` function.")

    def meta(self, property: str | None = None, default=None):
        """
        Query recorder-level metadata. With a ``property`` name return that entry
        (or ``default``); with no argument return a copy of the whole metadata
        mapping.
        """
        if property is None:
            return dict(self._meta)
        return self._meta.get(property, default)

    def set_meta(self, property: str, value) -> None:
        """Set a recorder-level metadata entry."""
        self._meta[property] = value


# ---- reader helper -----------------------------------------------------------


@dataclasses.dataclass
class Recording:
    """Flat view of a single recorded Neo object inside a ``.nio`` block."""

    ps_name: str
    cell_id: int
    device: str
    name: str
    units: str
    kind: type
    data: object
    annotations: dict


def read_nio(path: str) -> "neo.Block":
    """Open a ``.nio`` file and return its :class:`neo.Block`."""
    from neo import io

    return io.NixIO(path, mode="ro").read_block()


def iter_recordings(block) -> typing.Iterator[Recording]:
    """
    Yield one :class:`Recording` per Neo object across all segments.

    Skips Neo objects that lack a ``bsb_ps_name`` annotation (e.g. third-party
    plugin output that does not follow the convention).
    """
    for segment in block.segments:
        for obj in [*segment.spiketrains, *segment.analogsignals]:
            ann = dict(obj.annotations or {})
            ps_name = ann.get("bsb_ps_name")
            if ps_name is None:
                continue
            yield Recording(
                ps_name=ps_name,
                cell_id=int(ann.get("bsb_cell_id", -1)),
                device=ann.get("bsb_device_name", ""),
                name=getattr(obj, "name", "") or "",
                units=str(getattr(obj, "units", "") or ""),
                kind=type(obj),
                data=obj,
                annotations=ann,
            )


__all__ = [
    "Recording",
    "SimulationRecorder",
    "SimulationResult",
    "iter_recordings",
    "read_nio",
]
