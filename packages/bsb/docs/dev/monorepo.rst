Monorepo
========

The BSB uses a monorepo pattern for organizing the framework code, packages, and
first party plugins:

.. code-block::

    packages
    ├── bsb
    ├── bsb-core
    ├── ...
    libs
    └── ...

The ``bsb`` package contains a metadata-only package that will install the main
framework, and all of the bundled first-party plugins we recommend. The ``bsb-core``
package contains the main framework code. Any other packages under ``packages`` are
our first-party plugin packages, some of which will come bundled immediately when
you ``pip install bsb``, some won't.

The ``libs`` folder contains shared utility packages that are not interesting for
users to install, but we as developers might need multiple times over for a variety
of the packages we maintain.

The root of our source code repository houses all of the monorepo configuration
files. We use `Nx <https://nx.dev/>`_ as our monorepo manager, with the
`@nxlv/python <https://github.com/lucasvieirasilva/nx-plugins/blob/main/packages/nx-python/README.md>`_
plugin to adapt it to Python from its typical JS use-case.

.. _dev-install:

Installation
------------

.. start-dev-install

First, make sure you have followed the :ref:`Parallel support <parallel-guide>` guidelines.

In order for you to manage the monorepo aspects using ``nx``, you'll have to install
NodeJS. There is helper scripts for each platform in ``devtools/bootstrap-*``:

.. tab-set::

  .. tab-item:: Ubuntu
    :sync: bash

      .. code-block:: bash

        git clone https://github.com/dbbs-lab/bsb
        cd bsb
        ./devtools/bootstrap-linux.sh
        ./nx init

  .. tab-item:: MacOS
    :sync: bash

        .. code-block:: bash

          git clone https://github.com/dbbs-lab/bsb
          cd bsb
          ./devtools/bootstrap-mac.sh
          ./nx init

  .. tab-item:: Windows
    :sync: shell

        .. code-block:: bash

          git clone https://github.com/dbbs-lab/bsb
          cd bsb
          .\devtools\bootstrap-windows.ps1
          .\nx init

.. note::

    As a non-JavaScript Nx repo we use an alternative installation method which does
    not have a ``package.json`` file at the root, and instead declares its bootstrapping
    in the ``installation`` key of ``nx.json``. Whenever you run ``./nx``, the scripts - via
    ``.nx/nxw.js`` - will bootstrap an Nx installation in the ``.nx`` folder, with the typical
    ``package.json`` and ``node_modules`` maintained in the ``.nx/installation`` folder.

.. hint::

    You can ``npm install -g nx`` so that you can use regular ``nx`` command without having
    to point to the ``./nx`` path.

.. end-dev-install

Usage
-----

Nx works by providing you with a set of generators, and managing a collection of projects,
that can each define a set of targets that run certain executors.

Generators let you quickly create boilerplate, and make automated changes to all of your
projects in the monorepo, such as adding new projects, creating publishable Python package
stubs, ...

Each project in a monorepo represents a code entity that will produce its own set of output
artifacts, such as its own Python package that we'd publish to PyPI. e.g., ``bsb-yaml``,
``bsb-json``, ... These projects are independent once distributed to the public, but they're
gathered here in this monorepo because their tooling and release cycle tightly depend on
each other, and are a large burden to maintain separately. Without a monorepo we'd have X
PRs, X release cycles, X docfixes, ... with a monorepo that can all be done in 1 PR, 1 release cycle.

Each project is defined in ``project.json``, and there declares a set of targets, each with
an executor provided by Nx or a plugin. An executor runs a certain workflow, such as building,
linting, formatting, building docs, ...

Adding a project
~~~~~~~~~~~~~~~~

To add a project run the `@nxlv/python:uv-project` generator:

.. code-block::

    nx generate @nxlv/python:uv-project my-new-project

Running a target
~~~~~~~~~~~~~~~~

To run a target, use ``nx run`` followed by ``project:target``:

.. code-block:: bash

    nx run bsb-core:docs

This would build the `bsb-core` documentation.
You can also run the same target for all the projects that have it:

.. code-block:: bash

    nx run-many -t docs

Nx caches the targets that have been already completed successfully, so that it does not
re-run them if you did not modify the linked project. If you want Nx to force run a target,
ignoring the cache then use the ``--skipNxCache`` flag.

Main targets
~~~~~~~~~~~~

In practice, Nx uses `Uv <https://docs.astral.sh/uv/>`_ to create an independent python
environment (inside a ``.venv`` subfolder) for each of its subpackages. Uv will be installed
with Nx thanks to the ``devtools/bootstrap-*`` script.
Hence, some of the `Uv commands <https://docs.astral.sh/uv/reference/cli/>`_ are also
available through Nx:

- ``./nx run bsb-core:add my-package`` adds `my-package` to the list of dependencies of `bsb-core`
- ``./nx run bsb-core:remove my-package`` removes `my-package` to the list of dependencies of `bsb-core`
- ``./nx run bsb-core:sync`` updates the environment of `bsb-core` project based on its lock file and toml
- ``./nx run bsb-core:install`` similar to the ``sync`` command.
- ``./nx run bsb-core:lock`` updates the lock file of `bsb-core` project
- ``./nx run bsb-core:update`` will upgrade the libraries of the lock file when possible and ``sync`` the new environment.

.. hint::

    Note that you can run any command within each subpackage environment with uv:

    .. code-block:: bash

        cd packages/bsb-core
        uv run bsb compile [...]

Next are all the commands used in the development workflow:

- ``./nx run bsb-core:test`` performs the unittests for `bsb-core`
- ``./nx run bsb-core:docs`` builds the documentation for `bsb-core`
- ``./nx run bsb-core:lint`` checks if the code of `bsb-core` passes the lint tests with `ruff <https://docs.astral.sh/ruff/>`_
- ``./nx run bsb-core:format`` formats the code of `bsb-core` according to `black` guidelines
- ``./nx run bsb-core:build`` packages the code of `bsb-core`

The remaining commands are used to deploy the BSB on ``Pypi`` which should be done automatically by Github.
