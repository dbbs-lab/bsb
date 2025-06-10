.. _development-section:

####################
Developer Guidelines
####################

This section provides advisory guidelines for developers on the BSB repository to facilitate
the communication with its maintainer and smoothen the process of integration and review of new contributions.

Please, read first our `code of conduct <https://github.com/dbbs-lab/bsb/blob/main/CODE_OF_CONDUCT.md>`_  to
understand how to interact with the BSB community |:heart:|

Raise issue on Github
~~~~~~~~~~~~~~~~~~~~~
If you wish to contribute or raise an issue on the BSB project, you should first check the list of known
`issues <https://github.com/dbbs-lab/bsb/issues>`_ on Github. If you cannot find an issue related to your specific
contribution, please create a new one. It is indeed important for the BSB maintainers to keep track of potential bugs
or needed features to schedule future releases. Additionally, they would provide you with their expertise and guide you
through this process of development.

If you need to create an issue on Github, please provide as much context as possible.

Fork and create a Pull Request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
If you are not part of the BSB maintainers, you should
`fork <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo>`_
the bsb repository on your own account to modify the code.
If you introduce new features to BSB, please provide the associated documentation (docstrings or general documentation),
and unittests. We are trying to improve the coverage for both and would appreciate greatly your contribution.

The documentation, tests and code style is controlled for each commit on the repository, so please
install the :ref:`pre-commit hooks <dev-install>` and run the following tests before pushing on the repository:

.. code-block:: bash

  cd bsb
  ./nx run-many -t format  # format the code according to black
  ./nx run-many -t lint  # run ruff check
  ./nx run-many -t test  # unittest
  ./nx run-many -t docs  # check if documentations are building without warnings
  ./nx run bsb-core:check-api  # check bsb-core python API

The BSB repository implements Github Actions to perform these tests directly on Github. Failing these tests will prevent
the integration of your contribution. Do not hesitate to ask for help on these |:wink:|

When you believe your changes are ready to be integrated in the main repository, you can create a Pull Request (PR)
adding in the description what your contribution changed and which issue it is related to.

Commit guidelines
~~~~~~~~~~~~~~~~~
BSB commits and PR names should follow the
`conventional commits guidelines <https://www.conventionalcommits.org/en/v1.0.0>`_. Not only this will help with the
communication of the nature of your changes with the other developers, it will also permit for the automatic
generation of changelogs and releases.

Releases
~~~~~~~~
A new BSB release is published automatically for every push on the ``main`` branch.
The push will automatically trigger Github Actions that will bump the library version, add a git tag, make a github
release and update the `CHANGELOG <https://github.com/dbbs-lab/bsb/blob/main/CHANGELOG.md>`_
This will update the official documentation on ``Readthedocs`` but also deploy the code on
`PyPI <https://pypi.org/project/bsb/>`_.
