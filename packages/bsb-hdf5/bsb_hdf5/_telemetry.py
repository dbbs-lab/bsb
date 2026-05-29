import contextlib

from bsb_otel.tracer import get_bsb_tracer, local_tracing

_inner = get_bsb_tracer("bsb-hdf5")


class _LocalHdf5Tracer:
    """
    Tracer wrapper that always runs spans inside ``bsb_otel.tracer.local_tracing``.

    bsb-hdf5 file operations are per-rank — they're serialized across ranks
    via :class:`MPILock`, not via MPI collectives, so different ranks make
    different sequences of ``trace()`` calls. Letting bsb-otel attempt its
    cross-rank broadcast on these spans would deadlock as soon as the
    ranks diverge. Forcing :func:`bsb_otel.tracer.local_tracing` keeps each
    rank's bsb-hdf5 spans local while still inheriting any pre-existing
    broadcast parent set up higher in the call stack.
    """

    @staticmethod
    @contextlib.contextmanager
    def trace(name, attributes=None):
        with (
            local_tracing(),
            _inner.trace(name, attributes=attributes) as span,
        ):
            yield span


_hdf5_tracer = _LocalHdf5Tracer()
