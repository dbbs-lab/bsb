.. _components:

==============
BSB components
==============

The architecture of the BSB framework organizes your model's reconstruction and simulation
workflows into reusable code blocks: the components. The BSB offers many out of the box
of these components, covering most of the basic operations.

Documentation and Examples
--------------------------
For each of the BSB components, we provide examples of usage and documentation on their
parameters and outputs. You will find these at the following pages:

* :doc:`Topology </topology/intro>`, which includes :guilabel:`Regions` and :guilabel:`Partitions`,
* :doc:`Cell Types </cells/intro>`
* :doc:`Morphologies </morphologies/intro>` ,
* :doc:`Placement </placement/intro>`,
* :doc:`Connectivity </connectivity/defining>`,
* :doc:`Simulations </simulation/intro>`

If some aspects of the documentation are not sufficiently clear or missing, do not hesitate
to reach out for us.

Unfortunately, the BSB does not cover every use case and thus often you will need to write
your own components.

Writing components
------------------

Reaching out for help
^^^^^^^^^^^^^^^^^^^^^

Before diving into coding, do not hesitate to first reach out for us on our
`github page <https://github.com/dbbs-lab/bsb/issues>`_ to ask if there is
already a solution implemented for your use case. We can also provide you advice on how
to implement your component and might also be interested in integrating it directly into
the BSB itself. We greatly value user contributions to the BSB framework!
On this matter, if you wish to contribute to the BSB, check our
:doc:`guides for developers </dev/monorepo>`.


Code implementation
^^^^^^^^^^^^^^^^^^^

For each component, the BSB provides interfaces, each with a set of functions that you must
implement. By implementing these functions, the framework can seamlessly integrate your
custom components into a BSB workflow. Neat!

Here is how you do it (theoretically):

#. Identify which **interface** you need to extend. An interface is a programming concept
   that lets you take one of the objects of the framework and define some functions on it.
   The framework has predefined this set of functions and expects you to provide them.
   Interfaces in the framework are always classes.

#. Create a class that inherits from that interface and implement the required and/or
   interesting looking functions of its public API (which will be specified).

#. Refer to the class from the configuration by its importable module name, or use a
   :ref:`classmap`.

Check our step by step :doc:`tutorial </getting-started/guide_components>` on how to make
your own component.

Share your code with the whole world and become an author of a :ref:`plugin <plugins>`!
|:heart_eyes:|
