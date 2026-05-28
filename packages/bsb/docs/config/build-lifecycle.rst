.. _config_build_lifecycle:

##############################
Configuration build lifecycle
##############################

When a configuration file is loaded, BSB walks the parsed dict and constructs a
tree of :ref:`config nodes <config_nodes>`. This page explains the phases that
construction goes through, the hook points each phase exposes, and the
**build context**, a per-build shared scratchpad that nodes can use to
coordinate cross-cutting state without threading it through every constructor.

========
Overview
========

A full load goes through four phases:

1. **Parse**: :func:`~bsb.config.parse_configuration_file` (or a sibling) reads
   the file with the registered parser and produces a plain Python dict.
2. **Build**: the dict is handed to the :class:`~bsb.config.Configuration`
   root, which recursively casts every entry into typed config nodes. This is
   where ``required=``, ``type=``, and other attribute constraints are checked.
3. **Boot**: once the tree is complete the root walks every node and invokes
   each node's ``__boot__`` hook (if defined). Booting happens after the whole
   tree exists, so a node can safely reference siblings and parents here.
4. **Use**: the boot-complete tree is handed to a :class:`~bsb.core.Scaffold`
   and the workflow runs.

Phases 2 and 3 are the ones component authors hook into.

===============
Essential hooks
===============

``__post_new__``
================

Called by the framework after a node's attributes have been cast. Receives the
input ``kwargs`` and a fully-constructed instance. Use this when a node needs
to validate cross-attribute constraints or normalise derived state. The hook
runs **during** the build phase, while ancestor nodes may still be under
construction.

``__boot__``
============

Called after the entire tree is built and ``_config_isfinished`` is set on the
root. Use this when a node needs to look at sibling/parent values that may not
have existed at ``__post_new__`` time. ``__boot__`` runs once per tree load.

For a comparison with the wider hook system (``@config.before`` /
``@config.after`` / ``run_hook``) see :doc:`/dev/hooks`.

=================
The build context
=================

Some build-time validation needs resources that don't naturally live on any
single node, e.g. an out-of-process kernel to ask "does this synapse model
need a delay?". The build context is a ``ContextVar`` that is set when the
root build starts and cleared when it finishes. Anything registered on it is
visible to every constructor running underneath, and its
``cleanup_callbacks`` are guaranteed to run when the build exits (even on
error).

API
===

.. code-block:: python

  from bsb.config import (
      BuildContext,
      build_context,
      get_config_build_context,
      set_config_build_context,
  )

- :class:`~bsb.config.BuildContext`: namespace object with attribute access
  and auto-vivifying sub-namespaces, so packages can register their own
  scratch area as ``ctx.<pkg>.<name>`` without coordinating ahead of time.
- :func:`~bsb.config.get_config_build_context`: returns the active
  :class:`~bsb.config.BuildContext`, or ``None`` outside a build. Callers must
  handle the ``None`` case (typical pattern: warn and fall back).
- :func:`~bsb.config.build_context`: context manager that owns the lifecycle
  of a context. The root build wraps itself in this; you only call it
  yourself when you want strict build-time validation during a post-build
  mutation (see below).
- :func:`~bsb.config.set_config_build_context`: low-level setter used by the
  root build; rarely needed directly.

Registering a resource
======================

Resources are attached to a sub-namespace (one per package, by convention) and
paired with a cleanup callback that the context fires on exit:

.. code-block:: python

  from bsb.config import get_config_build_context

  def get_my_resource():
      ctx = get_config_build_context()
      if ctx is None:
          # No build in progress: caller decides what to do.
          return None
      existing = ctx.my_pkg.__dict__.get("resource")
      if existing is not None:
          return existing
      resource = _spawn_expensive_resource()
      ctx.my_pkg.resource = resource
      ctx.add_cleanup(resource.shutdown)
      return resource

Note the use of ``ctx.my_pkg.__dict__.get("resource")`` rather than
``getattr``: top-level sub-namespaces auto-vivify on read so callers can
``ctx.my_pkg.resource = x`` without setting up ``ctx.my_pkg`` first, but leaf
reads must go through ``__dict__`` to distinguish "not registered" from
"empty namespace".

Build context in ``required=`` checkers
========================================

The most common consumer of the build context is a callable
``required=`` (see :ref:`config_attrs_required_callable`). The pattern is to
treat "no build context" as "can't check, fall back gracefully":

.. code-block:: python

  from bsb import config, warn
  from bsb.config import get_config_build_context

  def _is_truly_required(kwargs):
      ctx = get_config_build_context()
      if ctx is None:
          warn("No active build context; treating field as optional.")
          return False
      # ... query a resource registered on `ctx` to decide ...

The build context is active during root construction
(:class:`Configuration({...}) <bsb.config.Configuration>` or any
:func:`~bsb.config.parse_configuration_file` path). It is **not** active when
mutating an already-built config (e.g. ``cfg.simulations[...] = {...}``),
because those go through ``ConfigurationAttribute.__set__`` directly. To get
strict build-time validation on such a mutation, wrap it yourself:

.. code-block:: python

  from bsb.config import build_context

  with build_context():
      cfg.simulations["test"] = {...}

================================
Example: NEST kernel as a proxy
================================

``bsb_nest`` uses the build context to validate synapse models without
importing NEST into the user's main process. ``bsb_nest.get_nest_kernel_proxy``
spawns a :class:`~multiprocessing.managers.BaseManager` subprocess on first
call, registers the proxy at ``ctx.bsb_nest.kernel``, and adds a cleanup
callback that shuts the subprocess down when the build context exits. The
``required=`` checker on a synapse's ``delay`` then asks the proxy whether
``has_delay`` is true for the chosen model, all without ever touching NEST's
global state in the caller. See ``bsb_nest._kernel_proxy`` for the
implementation.
