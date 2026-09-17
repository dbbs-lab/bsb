.. _guide_analyze_analog:

########################################
Analyze multi-compartment neuron results
########################################

.. note::

    This guide is a continuation of the
    :doc:`Simulation guide <guide_neuron>`.

After a simulation, BSB will write its outcomes in ``.nio`` files. These files leverage the HDF5
(Hierarchical Data Format version 5) format, which is widely employed in scientific computing,
engineering, and data analysis. HDF5 files store data in groups (or blocks), in a dictionary
fashion, which allows for efficient management and organization of large datasets.

The content is read/written using the :doc:`Neo Python package <neo:index>`, a library designed
for handling electrophysiology data.

Let's extract the spike train data produced by your last simulation. A recording only stores
the id of the cell it belongs to; it doesn't store the cell's position for instance.
That information lives in the network, so results must be loaded together with the network they were simulated on.
Load your ``simulation-results/NAME_OF_YOUR_NEO_FILE.nio`` file with the following code:

.. literalinclude:: /../../../examples/neuron-simulation/scripts/analyze_analog_results.py
    :language: python
    :lines: 1-7

:func:`~bsb.simulation.results.read_results` checks that the results were produced by this network
before it returns anything. The function returns a :class:`~bsb.simulation.results.ResultsReader`
class that contains all the ``recordings`` performed during the simulation. You can filter these recordings by
``kind`` (e.g.: "cell" or "synapse") or by ``device`` name: if you followed the previous simulation example,
the :guilabel:`analogsignals` attribute in the block
should contain a list of all measured signals: the membrane potential recorded by the
:guilabel:`vrecorder` device and the synapse current obtained from the :guilabel:`synapses_rec` device.

.. literalinclude:: /../../../examples/neuron-simulation/scripts/analyze_analog_results.py
    :language: python
    :lines: 9-12

Each recording (see :class:`~bsb.simulation.results.Recording`) holds the traces
of one cell under ``signal`` (see :class:`AnalogSignal <neo.core.AnalogSignal>`), and
``annotations`` contains additional information such as the target id in the simulation,
or the synapse type.

.. literalinclude:: /../../../examples/neuron-simulation/scripts/analyze_analog_results.py
    :language: python
    :lines: 13-37

This code generates 2 plots: one for a postsynaptic synapse current and one for the membrane
potential. The resulting figures are saved in the ``simulation-results`` folder.

Here are some examples of the figures that are produced:

.. figure:: /images/vrecorder_example.png
  :figwidth: 90%

  Example of the membrane potential recorded.

.. figure:: /images/synapse_recorder_example.png
  :figwidth: 90%

  Example of the AMPA synapse current recoded.

.. rubric:: Next steps:

.. grid:: 1 1 1 2
    :gutter: 1


    .. grid-item-card:: :octicon:`tools;1em;sd-text-warning` Make custom components
       :link: guide_components
       :link-type: ref

       Learn how to write your own components to e.g. place or connect cells.

    .. grid-item-card:: :octicon:`repo-clone;1em;sd-text-warning` Command-Line Interface
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
