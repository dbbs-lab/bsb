How to run repeated simulations
*******************************

Let us imagine that you want to run a list of simulations but only want to change one or many parameters
in between these simulations.
For the sake of this example, we suppose that you are using the reconstruction from the
:doc:`NEST tutorial</getting-started/simulations/guide_nest>`. We want here to run ``10`` iterations of the
``basal_activity`` simulation, only changing the ``rate`` parameter from the ``background_noise``
Poisson generator.

You could copy paste all these simulations in your configuration file or use the
:ref:`import mechanism <cfg_file_import>`, but this is a tedious task and prone to error.

Instead, you can load your simulation configuration from your Scaffold object and modify it on the fly:

.. code-block:: python

    from bsb import from storage

    scaffold = from_storage("network.hdf5")
    config_sim = scaffold.config.simulations["basal_activity"]

    nb_repetitions = 10
    for i in range(nb_repetitions):
            # Set the stimulation rate on the `general_noise` device
            input_rate = i * 10.0
            config_sim.devices["general_noise"].rate = input_rate
            # Run the simulation and collect the results
            results = scaffold.run_simulation("basal_activity")

            # save the results in a separate nio file
            output_file = f"simulation-results/my_simulation_results_{input_rate}Hz.nio"
            results.write(output_file, "ow")

.. note::

    In the above example, note that BSB will load your whole simulation parameters
    on NEST `10` times, which might take a while.

Let us say now that you want to directly modify a NEST variable. Then you will
have to use the :class:`SimulatorAdapter <bsb:bsb.simulation.adapter.SimulatorAdapter>`
related to NEST, the :class:`NestAdapter<bsb_nest:bsb_nest.adapter.NestAdapter>`.

To run a simulation directly with its adapter, you need to run this following methods:

- :meth:`adapter.prepare(sim) <bsb:bsb.simulation.adapter.SimulatorAdapter.prepare>`
  This method will load the scaffold parameters onto the simulator and returns its
  :class:`simulation backend<bsb:bsb.simulation.adapter.SimulationData>`
- :meth:`adapter.run(sim) <bsb:bsb.simulation.adapter.SimulatorAdapter.run>`
  This method run the actual simulation on the simulator and returns its results
- :meth:`adapter.collect(results) <bsb:bsb.simulation.adapter.SimulatorAdapter.collect>`
  This method will flush the results from completed simulations.

NEST additionally need you to reset its kernel in between simulations so you should run also the
:meth:`adapter.reset_kernel()<bsb_nest:bsb_nest.adapter.NestAdapter.reset_kernel>` before ``prepare``.

In between ``prepare`` and ``run`` you have a full access to the ``simulation backend``
in case you want to modify them directly:

.. literalinclude:: /../../../examples/nest-simulation/scripts/repeated_simulations.py
    :language: python