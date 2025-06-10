#############
Documentation
#############

The libraries necessary for building the documentation of each subpackage can be installed
through the ``docs`` option. For instance, with `bsb-core`:

.. code-block:: bash

  pip install bsb-core[docs]

You should have these libraries already if you have installed the bsb with nx,
with the `editable-install.txt` script, or with the ``dev`` flag.
You can build the documentations for each package with the following command (here shown for bsb-core):

.. tab-set::
  .. tab-item:: With nx
    :sync: bash

    .. code-block:: bash

      ./nx run bsb-core:docs

  .. tab-item:: Within a python env
    :sync: bash

    .. code-block:: bash

      cd packages/bsb-core/docs
      make html

The output will be inside the subpackages folder, under the ``/docs/_build`` folder.

.. note::
    Note that the command ``make html`` by default does not show you warnings in the documentations.
    These warnings will not pass the tests on the Github repository. To test if the documentations
    was properly implemented, prefer the command:

    .. code-block:: bash

        sphinx-build -nW -b html . _build/html

Conventions
===========

| Except for the files located at the root of the project (e.g.: README.md), the documentation is written in
  `reStructuredText <https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html>`_ . Docstrings
  in the python code should therefore be in the reStructuredText (``reST``) format.
| In the documentation, the following rules should be implemented:

* Values are marked as ``5`` or ``"hello"`` using double backticks (\`\` \`\`).
* Configuration attributes are marked as :guilabel:`attribute` using the guilabel
  directive (``:guilabel:`attribute```)
