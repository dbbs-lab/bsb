.. _guide_analyze_results:

##############################
Analyze spike activity results
##############################

.. note::

    This guide is a continuation of the
    :doc:`Simulation guide <guide_nest>`.

After a simulation, BSB will write its outcomes in ``.nio`` files. These files leverage the HDF5
(Hierarchical Data Format version 5) format, which is widely employed in scientific computing,
engineering, and data analysis. HDF5 files store data in groups (or blocks), in a dictionary
fashion, which allows for efficient management and organization of large datasets.

The content is read/written using the :doc:`Neo Python package <neo:index>`, a library designed
for handling electrophysiology data.

Let's extract the spike train data produced by your last simulation. A recording names the cell it
belongs to, but only the network knows where that cell is and what it is, so the results are read
together with the network they were simulated on. Load your
``simulation-results/NAME_OF_YOUR_NEO_FILE.nio`` file with the following code:

.. literalinclude:: /../../../examples/nest-simulation/scripts/analyze_spike_results.py
    :language: python
    :lines: 1-8

:func:`~bsb.simulation.results.read_results` checks that the results were produced by this network
before it returns anything. If you followed the previous simulation example, the results hold the
spikes recorded by :guilabel:`base_layer_record` and :guilabel:`top_layer_record`.

Each recording holds the spikes of one cell, and ``recording.target`` is that cell in the network:
its ``id`` in its placement set, its ``position``, its ``cell_type``, and its ``placement_set``.
A device records every cell it targeted, including the ones that never fired:

.. literalinclude:: /../../../examples/nest-simulation/scripts/analyze_spike_results.py
    :language: python
    :lines: 10-36

This code should produce one figure with 2 subplots showing the raster plot of spiking activity
for each spike recorder of the simulation. The resulting figure is saved in the
``simulation-results`` folder. The plot for the base type cells should show some spike events:

.. figure:: /images/raster_base_types.png
  :figwidth: 90%

These events indicates that some cells are receiving more spikes from the generator.

Various analyses can be perform on spiking data, and several tools facilitate these.
If you want to learn more about spike analysis, we recommend the
`Elephant <https://elephant.readthedocs.io/en/latest/index.html>`_ python package already
integrates `Neo`, and the
`Analysis of Parallel Spike Trains <https://link.springer.com/content/pdf/10.1007/978-1-4419-5675-0.pdf>`_
and the `Neuronal Dynamics <https://neuronaldynamics.epfl.ch/index.html>`_ books on this topic.

.. rubric:: Next steps:

.. grid:: 1 1 1 2
    :gutter: 1


    .. grid-item-card:: :octicon:`tools;1em;sd-text-warning` Make custom components
       :link: guide_components
       :link-type: ref

       Learn how to write your own components to e.g. place or connect cells.

    .. grid-item-card:: :octicon:`tools;1em;sd-text-warning` Command-Line Interface
        :link: cli-guide
        :link-type: ref

        Familiarize yourself with BSB's CLI.

    .. grid-item-card:: :octicon:`gear;1em;sd-text-warning` Learn about Components
       :link: components
       :link-type: ref

       Explore more about the main components.

    .. grid-item-card:: :octicon:`device-camera-video;1em;sd-text-warning` Examples
        :link: examples
        :link-type: ref

        Explore more advanced examples
