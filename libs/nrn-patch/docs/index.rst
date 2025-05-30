.. Patch documentation master file, created by
   sphinx-quickstart on Fri Jan 24 15:06:28 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Patch's documentation!
=================================

.. image:: https://badge.fury.io/gh/Helveg%2Fpatch.svg
    :target: https://badge.fury.io/gh/Helveg%2Fpatch

.. image:: https://github.com/Helveg/patch/actions/workflows/main.yml/badge.svg

.. image:: https://codecov.io/gh/Helveg/patch/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/Helveg/patch

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

.. image:: https://readthedocs.org/projects/patch/badge/?version=latest
    :target: https://patch.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   usage
   sections
   connections
   magic
   patch
   candy_guide

Installation
------------

Patch can be installed using::

   pip install nrn-patch

Syntactic sugar & quality of life
---------------------------------

This wrapper aims to make NEURON more robust and user-friendly, by patching common
gotcha's and introducing sugar and quality of life improvements. For a detailed overview
of niceties that will keep you sane instead of hunting down obscure bugs, check out the
:doc:`candy_guide`.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
