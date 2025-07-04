.. DBBS Cerebellum Scaffold documentation master file, created by
   sphinx-quickstart on Tue Oct 29 12:24:53 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

The Brain Scaffold Builder
==========================

The BSB is a **black box component framework** for multi-paradigm neural modelling: we
provide structure, architecture and organization, while you provide the use-case specific
parts of your model. In our framework, your model is described in a code-free
configuration of **components** with parameters.

For the framework to reliably use components, and make them work together in a complex
workflow, it asks a fixed set of questions per component type: e.g. a connection component
will ask how to connect cells. These contracts of cooperation between you and the
framework are called **interfaces**. The framework executes a transparently
parallelized workflow, and calls your components to fulfill their role.

This way, by *implementing our component interfaces* and declaring them in a
configuration file, most models end up being code-free, well-parametrized, self-contained,
human-readable, multi-scale models!

(PS: If we missed any hyped-up hyphenated adjectives, let us know! |:heart:|)

----

.. grid:: 1 1 4 2
    :gutter: 1

    .. grid-item-card:: :octicon:`desktop-download;1em;sd-text-warning` Installation
      :link: installation-guide
      :link-type: ref

      How to install the code.

    .. grid-item-card:: :octicon:`flame;1em;sd-text-warning` Get started
      :link: get-started
      :link-type: ref

      Get started with your first project!

    .. grid-item-card:: :octicon:`device-camera-video;1em;sd-text-warning` Examples
       :link: examples
       :link-type: ref

       View examples explained step by step

    .. grid-item-card:: :octicon:`repo-clone;1em;sd-text-warning` BSB - CLI
       :link: cli-guide
       :link-type: ref

       Learn how to use the Command-Line Interface.

    .. grid-item-card:: :octicon:`tools;1em;sd-text-warning` Contributing
       :link: development-section
       :link-type: ref

       Help out the project by contributing code.

    .. grid-item-card:: :octicon:`gear;1em;sd-text-warning` Learn about Components
       :link: main-components
       :link-type: ref

       Explore more about the main components.

    .. grid-item-card:: :octicon:`briefcase;1em;sd-text-warning` Python API
       :link: bsb:whole-api
       :link-type: ref


    .. grid-item-card:: :octicon:`info;1em;sd-text-warning` FAQ
       :link: faq
       :link-type: ref

Content
-------

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   getting-started/installation
   getting-started/toc
   examples/toc

.. toctree::
   :maxdepth: 2
   :caption: Framework concepts

   /core/scaffold
   /config/configuration-toc
   /core/storage
   /core/job-distribution

.. toctree::
   :maxdepth: 2
   :caption: Domains

   /topology/topology-toc
   /cells/cells-toc
   /morphologies/morphology-toc
   /placement/placement-toc
   /connectivity/connectivity-toc
   /simulation/simulation-toc
   /components/components

.. toctree::
  :maxdepth: 2
  :caption: Command-Line Interface

  /cli/intro
  /cli/commands
  /cli/options

.. toctree::
   :maxdepth: 2
   :caption: References

   bsb-core <https://bsb-core.readthedocs.io/en/latest/bsb/modules.html>
   bsb-hdf5 <https://bsb-hdf5.readthedocs.io/en/latest/bsb_hdf5/modules.html>
   bsb-json <https://bsb-json.readthedocs.io/en/latest/bsb_json/modules.html>
   bsb-yaml <https://bsb-yaml.readthedocs.io/en/latest/bsb_yaml/modules.html>
   bsb-arbor <https://bsb-arbor.readthedocs.io/en/latest/bsb_arbor/modules.html>
   bsb-nest <https://bsb-nest.readthedocs.io/en/latest/bsb_nest/modules.html>
   bsb-neuron <https://bsb-neuron.readthedocs.io/en/latest/bsb_neuron/modules.html>

.. toctree::
   :maxdepth: 1
   :caption: FAQ

   dev/faq

.. toctree::
  :maxdepth: 2
  :caption: Developer Guides:

  dev/dev-toc
