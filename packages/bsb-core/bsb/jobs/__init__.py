"""
Job workflow machinery.

This module owns the BSB *workflow layer*: :class:`JobPool`, job submission,
dependency tracking, listeners, and :func:`pool_cache`. The thin concurrency
backend is consumed from :mod:`bsb.services.pool`; backend selection happens
there.
"""

from ._listeners import (
    JobTally,
    Listener,
    NonTTYTerminalListener,
    PoolTally,
    TTYTerminalListener,
)
from ._pool import (
    ConnectivityJob,
    FunctionJob,
    Job,
    JobErroredError,
    JobPool,
    JobStatus,
    PlacementJob,
    PoolJobAddedProgress,
    PoolJobUpdateProgress,
    PoolProgress,
    PoolProgressReason,
    PoolStatus,
    PoolStatusProgress,
    SubmissionContext,
    Workflow,
    WorkflowError,
    dispatcher,
    free_stale_pool_cache,
    get_node_cache_items,
    pool_cache,
)

__all__ = [
    "ConnectivityJob",
    "FunctionJob",
    "Job",
    "JobErroredError",
    "JobPool",
    "JobStatus",
    "JobTally",
    "Listener",
    "NonTTYTerminalListener",
    "PlacementJob",
    "PoolJobAddedProgress",
    "PoolJobUpdateProgress",
    "PoolProgress",
    "PoolProgressReason",
    "PoolStatus",
    "PoolStatusProgress",
    "PoolTally",
    "SubmissionContext",
    "TTYTerminalListener",
    "Workflow",
    "WorkflowError",
    "dispatcher",
    "free_stale_pool_cache",
    "get_node_cache_items",
    "pool_cache",
]
