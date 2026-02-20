.. _faq:

###
FAQ
###

.. dropdown:: How to make the BSB work with NEST and MUSIC in an MPI context?
    :animate: fade-in-slide-down

    .. rubric:: Context

    When I simulate/reconstruct my BSB network in a context with `NEST` and `MUSIC` in parallel
    (with `MPI`), I encounter the following bug:

    .. code-block:: bash

        [ERROR] [2024.11.26 16:13:3 /path/to/nest-simulator/nestkernel/mpi_manager.cpp:134 @ MPIManager::init_mpi()] :
        When compiled with MUSIC, NEST must be initialized before any other modules that call MPI_Init(). Calling MPI_Abort().
        --------------------------------------------------------------------------
        MPI_ABORT was invoked on rank 0 in communicator MPI_COMM_WORLD
        with errorcode 1.

        NOTE: invoking MPI_ABORT causes Open MPI to kill all MPI processes.
        You may or may not see output from other processes, depending on
        exactly when Open MPI kills them.
        --------------------------------------------------------------------------

    .. rubric:: Explanation

    This issue happens because MUSIC requires you to prepare the NEST context before the MPI context.
    In other words, you should import ``nest`` before importing ``mpi4py`` if you have installed NEST
    with MUSIC. Yet, the BSB leverages MPI for parallelizing the tasks of reconstructing or simulating
    your network, so it imports mpi4py.

    Using the BSB with NEST and MUSIC is therefore only possible through python scripts.
    At the start of the python scripts that needs to import bsb, add an extra line before to import
    nest even if you are not using it:

    .. code-block:: python

        import nest
        from bsb import Scaffold

        # rest of your code here.

    .. rubric:: Advanced MPI options

    Note that if you manually create the MPI communicator with a subgroup of cores available
    and pass it to your BSB Scaffold, it will also set the MPI communicator for NEST.
    If you need a different MPI communicator between NEST and BSB, you should set it manually once the `NESTAdapter` has been prepared
    (see also this :doc:`BSB-NEST example</examples/nest_repeated_sim>`):

    .. code-block:: python

        import nest
        from mpi4py import MPI
        from bsb import from_storage
        from bsb_nest import NestAdapter

        # We take all cores for NEST
        comm_nest = MPI.COMM_WORLD

        # We do not take the last core for BSB
        comm_bsb = MPI.COMM_WORLD.Create_group(
            MPI.COMM_WORLD.group.Excl([MPI.COMM_WORLD.Get_size() - 1])
        )

        scaffold = from_storage("network.hdf5", comm=comm_bsb)
        simulation = scaffold.get_simulation("basal_activity")
        adapter = NestAdapter()
        adapter.reset_kernel()
        simulation_backend = adapter.prepare(simulation)
        # Set NEST communicator here
        nest.set_communicator(comm_nest)
        # rest of your code here.

.. dropdown:: When do I need to recompile my Scaffold?
    :animate: fade-in-slide-down

    .. rubric:: Context

    I have created a configuration and ``compiled`` it which produced a scaffold storage
    file. Now, I have made modification to my configuration file and I want to update the
    storage file. Is it necessary to recompile entirely my network?

    .. rubric:: Explanation

    The BSB's reconstruction phase is separated from the simulation. So if you want to
    make modifications to the ``simulations`` section of the BSB then you only need to
    run the reconfigure command to update the stored configuration file:

    .. code-block:: bash

        bsb reconfigure network.hdf5 network_configuration.json

    If otherwise you have changed part of the configuration related to a specific step
    in the reconstruction pipeline, you can use the ``--redo`` with the ``--only``, or
    ``--skip`` flags:

    .. code-block:: bash

        bsb compile --redo --skip-placement # Redo all reconstruction steps except placement
        bsb compile --redo --only=stratA,stratB # Redo only stratA and stratB strategies
                                                # and all strategies that depends on it.
        bsb compile --redo --skip=stratA # Redo all configuration except stratA

    If you have added a new strategy or you want to duplicate its results,
    you can instead use ``append``:

    .. code-block:: bash

        bsb compile --append --only=stratA # Run only stratA and its dependencies.
                                           # Append the results to the ones already generated

    You can see all the ``compile`` flags options in :ref:`bsb_compile`.
    If you modified the topology of the Scaffold, since most of the reconstruction
    pipeline depends on it, you should recompile your whole network:

    .. code-block:: bash

        bsb compile --redo
