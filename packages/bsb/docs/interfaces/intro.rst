Interfaces
==========

An interface, in programming, is a contract that separates *what* a piece of code
does from *how* it does it. The framework holds the *what*. An implementation behind
the interface provides the *how*. Two implementations of the same interface are
substitutable: the rest of the system does not care which one is in use as long as
both honor the contract.

The BSB is a component framework, and almost every moving part it has is defined
behind an interface. Placement strategies, connection strategies, cell types,
partitions, regions, morphology selectors, morphology parsers, simulation backends,
simulator adapters, devices, cell models, connection models, storage engines, file
stores, placement sets, connectivity sets, morphology repositories, configuration
parsers, configuration nodes, after-placement and after-connectivity hooks, services,
controllers: each is an interface, and most of them have more than one implementation
in the wild.

This section is the place to find the full, prescriptive description of those
interfaces. For each interface documented here you can expect to find:

* the abstract base class and the methods an implementation must provide;
* the expected lifecycle (when each method is called, by whom, in which order);
* the data model the implementation owns and the invariants it must maintain;
* the optional methods, defaults, and convenience helpers the framework offers;
* a worked walkthrough pointing at the reference implementation(s) in the
  monorepo.

For the orthogonal question of how an implementation gets *registered* with the BSB
through Python entry points (so the framework can discover it at runtime), see
:ref:`plugins`. The pages in this section assume that mechanism as background and
focus on the contracts themselves.
