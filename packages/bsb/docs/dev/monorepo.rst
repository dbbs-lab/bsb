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
files. We use [Nx](https://nx.dev/) as our monorepo manager, with the
[@nxlv/python](https://github.com/lucasvieirasilva/nx-plugins/blob/main/packages/nx-python/README.md)
plugin to adapt it to Python from its typical JS use-case.

Installation
------------

In order for you to manage the monorepo aspects using ``nx``, you'll have to install
NodeJS. There's helper scripts for each platform in ``devtools/bootstrap-*``. For Linux:

    source ./devtools/bootstrap-linux.sh

.. note::

    As a non-JavaScript Nx repo we use an alternative installation method which does
    not have a ``package.json`` file at the root, and instead declares its bootstrapping
    in the ``installation`` key of ``nx.json``. Whenever you run ``./nx``, the scripts - via
    ``.nx/nxw.js`` - will bootstrap an Nx installation in the ``.nx`` folder, with the typical
    ``package.json`` and ``node_modules`` maintained in the ``.nx/installation`` folder.

.. hint::

    You can ``npm install -g nx`` so that you can use regular ``nx`` command without having
    to point to the ``./nx`` path.

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

.. code-block::

    nx run bsb-core:docs

This would build the `bsb-core` documentation.