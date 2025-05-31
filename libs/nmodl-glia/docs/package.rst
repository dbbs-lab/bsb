Packaging
=========

Glia packages use ``flit``:

.. code-block:: bash

  pip install flit

Creating a package
------------------

Use the following command, and fill out the prompts:

.. code-block:: bash

  glia pkg new

This creates a template package that can be immediately published with ``flit publish``.
You can change the version inside of ``__init__.py`` by changing ``__version__``.

Adding mod files
----------------

Use the following command, and fill out the prompts:

.. code-block:: bash

  glia pkg add path/to/file.mod

You can specify a different ``--name`` and ``--variant``. Defaults to the file name without
extension and ``"0"`` respectively.