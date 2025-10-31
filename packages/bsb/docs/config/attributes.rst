.. _config_attrs:

########################
Configuration attributes
########################

An attribute can refer to a singular value of a certain type, a dict, list, reference, or
to a deeper node. You can use the :func:`config.attr <bsb:bsb.config.attr>` in node decorated
classes to define your attribute:

.. code-block:: python

  from bsb import config

  @config.node
  class CandyStack:
    count = config.attr(type=int, required=True)
    candy = config.attr(type=CandyNode)

.. code-block:: json

  {
    "count": 12,
    "candy": {
      "name": "Hardcandy",
      "sweetness": 4.5
    }
  }

.. _config_dict:

Configuration dictionaries
==========================

Configuration dictionaries hold configuration nodes. If you need a dictionary of values
use the :func:`types.dict <bsb:bsb.config.types.dict>` syntax instead.

.. code-block:: python

  from bsb import config

  @config.node
  class CandyNode:
    name = config.attr(key=True)
    sweetness = config.attr(type=float, default=3.0)

  @config.node
  class Inventory:
    candies = config.dict(type=CandyStack)

.. code-block:: json

  {
    "candies": {
      "Lollypop": {
        "sweetness": 12.0
      },
      "Hardcandy": {
        "sweetness": 4.5
      }
    }
  }

Items in configuration dictionaries can be accessed using dot notation or indexing:

.. code-block:: python

  inventory.candies.Lollypop == inventory.candies["Lollypop"]

Using the ``key`` keyword argument on a configuration attribute will pass the key in the
dictionary to the attribute so that ``inventory.candies.Lollypop.name == "Lollypop"``.

.. _config_list:

Configuration lists
===================

Configuration dictionaries hold unnamed collections of configuration nodes. If you need a
list of values use the :func:`types.list <bsb:bsb.config.types.list>` syntax instead.

.. code-block:: python

  from bsb import config

  @config.node
  class InventoryList:
    candies = config.list(type=CandyStack)

.. code-block:: json

  {
    "candies": [
      {
        "count": 100,
        "candy": {
          "name": "Lollypop",
          "sweetness": 12.0
        }
      },
      {
        "count": 1200,
        "candy": {
          "name": "Hardcandy",
          "sweetness": 4.5
        }
      }
    ]
  }

.. _config_ref:

Configuration references
========================

Reference attributes are ways to refer to other locations in the configuration.
Upon loading the configuration, the referred value will be fetched from
the referenced node:

.. code-block:: json

  {
    "locations": {"A": "very close", "B": "very far"},
    "where": "A"
  }

Assuming here that ``where`` is a reference attribute, referring to ``locations``,
location ``A`` will be retrieved and used as the value for ``where``. You can access
references like normal configuration attributes:

.. code-block:: python

  >>> print(conf.where)
  'very close'

Reference attributes are defined inside the configuration nodes by passing a
:ref:`quick-reference-lambda` to the :func:`bsb:bsb.config.ref` function.

.. code-block:: python

  def my_ref_lambda(root, here):
    # This function will be called to find the location of the references
    # within the configuration. Either from the `root` of the configuration
    # or from the node containing the ref attribute (`here`)
    return here["locations"]

  @config.node
  class Locations:
    locations = config.dict(type=str)
    where = config.ref(my_ref_lambda)

  # Or even shorter, with a true lambda:
  @config.node
  class Locations:
    locations = config.dict(type=str)
    where = config.ref(lambda root, here: here["locations"])

.. note::
    Make sure that you understand what each of the reference terms correspond to:

    - ``where`` is here a reference attribute or referrer
    - ``my_ref_lambda`` is a reference lambda
    - ``locations`` is the referenced object or referee
    - ``'A'`` is the reference key
    - ``'very close'`` is the reference value

You can also create a reference list attribute in your node class with the
:func:`bsb:bsb.config.reflist` function. Then, you should provide a list of
reference keys in the configuration file:

.. code-block:: json

  {
    "locations": {"A": "very close", "B": "very far"},
    "where": ["A", "B"]
  }

.. code-block:: python

    @config.node
    class Locations:
        locations = config.dict(type=str)
        where = config.reflist(lambda root, here: here["locations"])

.. warning::
  Note that reference lists are quite indestructible; setting them to ``None`` just resets them.

Many nodes of the BSB Configuration contain reference attributes. For instance,
a ``placement`` node contains reference list attributes to the ``cell_types`` and ``partitions``.

.. _quick-reference-lambda:

Reference lambdas
-----------------

The minimal implementation of a reference lambda is a function which returns
the node containing referred values starting from the configuration's
``root`` node or the current node (``here``):

.. code-block:: python

  @config.node
  class Locations:
      locations = config.dict(type=str)
      where = config.ref(lambda root, here: here["locations"])

The BSB also provides the :class:`Reference<bsb:bsb.config.Reference>` class.
Through this interface, you can provide reference lambdas with more advanced behavior:

1. The ``type`` property can be set so that the reference lambda can be used when ``reference_only=False``.

.. code-block:: python

    class CellTypeReference(Reference):
        def __call__(self, root, here):
            # This function will be called to find the cell types
            # located at the root of the Configuration
            return root.cell_types

        @property
        def type(self):
            # This function will be called to cast values
            # when `reference_only=False` and should return a
            # type handler.
            from bsb import CellType

            return CellType

    @config.node
    class Locations:
        cell_type = config.ref(CellTypeReference())

2. The ``has_ref``, ``has_ref_value``, ``get_ref``, and ``get_ref_name`` methods can be added
   so that the referenced object returned from ``__call__`` does not need to be a config node,
   dict, or list, but can be a customized object for advanced referencing:

.. code-block:: python

    class OnlyMinMaxLayerReference(Reference):
        """
        References the largest or smallest layer in the model, depending
        on whether the reference key "max" or "min" was given.
        """
        def __call__(self, root, here):
            # Filter out all the Layers into a set
            return {p for p in root.partitions if isinstance(p, Layer)}

        def has_ref(self, remote, key):
            # If there were any layers, we will have a ref
            return len(remote) and (key == "min" or key == "max")

        def has_ref_value(self, remote, value):
            # We don't want people to pass in just any Layer, they
            # have to pass in "min" or "max"
            return False

        def get_ref(self, remote, key):
            if key == "min":
                return min(remote, key=lambda l: l.volume)
            elif key == "max":
                return max(remote, key=lambda l: l.volume)

        def get_ref_name(self, remote):
            return "smallest or largest layer in {root}.partitions"

Referred object casting
-----------------------

On top of the Reference object, you can pass some parameters to a reference attribute to
enforce the casting of the referred value:

- ``ref_type``: A type handler for the reference attribute. Values that can't be found
  as a reference will be cast to this type. If that fails as well an error is raised.
- ``reference_only``: Boolean flag that when true disables casting of values, in effect
  enforcing that every value passed to this attribute must be found as a reference and may
  not be a new value not found in the referenced object. By default, it is set to ``True``.

With ``reference_only`` set to ``False``, you can provide either a reference or castable
value:

.. code-block:: python

    def my_ref_object(root, here):
        return here["locations"]

    @config.node
    class Locations:
        locations = config.dict(type=str)
        where = config.reflist(my_ref_object, reference_only=False)

.. code-block:: json

  {
    "locations": {"A": "very close", "B": "very far"},
    "where": ["A", {"C": "local"}]
  }

.. code-block:: python

  >>> print(conf.where)
  ['very close', 'local']

After the configuration is loaded, it is possible to either give a new reference key
(usually a string) or a new reference value. In most cases, the configuration will
automatically detect what you are passing into the reference:

.. code-block::

  >>> cfg.placement.general_placement.partitions.granular_layer.name
  'granular_layer'
  >>> cfg.placement.general_placement.partitions.granular_layer = 'molecular_layer'
  >>> cfg.placement.general_placement.partitions.granular_layer.name
  'molecular_layer'
  >>> cfg.placement.general_placement.partitions.granular_layer = cfg.partitions.purkinje_layer
  >>> cfg.placement.general_placement.partitions.granular_layer
  'purkinje_layer'

As you can see, by passing the reference a string the object is fetched from the reference
location, but we can also directly pass the object the reference string would point to.

Bidirectional references
------------------------

The referenced node can be "notified" that it is being referenced by the
``populate`` of the reference attribute.
This mechanism stores the referrer instance on the referenced node creating a
bidirectional reference. During configuration references resolution, the referrer will append
its instance to the list on the referee under the attribute given by the referred value
(or create a new list if it doesn't exist).

.. code-block:: json

  {
    "containers": {
      "A": {}
    },
    "elements": {
      "a": {"container": "A"}
    }
  }

.. code-block:: python

  @config.node
  class Container:
    name = config.attr(key=True)
    elements = config.attr(type=list, default=list, call_default=True)

  def container_ref(root, here):
    return root.containers

  @config.node
  class Element:
    container = config.ref(container_ref, populate="elements")

This would result in ``cfg.containers.A.elements == [cfg.elements.a]``.

You can overwrite the default *append or create* population behavior by creating a
descriptor for the referenced attribute and define a ``__populate__`` method on it:

.. code-block:: python

  class PopulationAttribute:
    # Standard property-like descriptor protocol
    def __get__(self, instance, objtype=None):
      if instance is None:
        return self
      if not hasattr(instance, "_population"):
        instance._population = []
      return instance._population

    # Prevent population from being overwritten
    # Merge with new values into a unique list instead
    def __set__(self, instance, value):
      instance._population = list(set(instance._population) + set(value))

    # Example that only stores referrers if their name in the configuration is "square".
    def __populate__(self, instance, value):
      print("We're referenced in", value.get_node_name())
      if value.get_node_name().endswith(".square"):
        self.__set__(instance, [value])
      else:
        print("We only store referrers coming from a .square configuration attribute")

  @config.node
  class Container:
    name = config.attr(key=True)
    elements = config.attr(type=PopulationAttribute)

  def container_ref(root, here):
    return root.containers

  @config.node
  class Element:
    container = config.ref(container_ref, populate="elements")

In the previous example, we were making sure that each value stored in the ``PopulationAttribute``
was unique by leveraging the ``set`` type. Note that you can also set the boolean flag
``pop_unique`` (``True`` by default) of the referrer (here ``Element.container``) and pass it as
the ``unique_list`` parameter to the ``__populate__`` method of the referee attribute.

.. code-block:: python

  class PopulationAttribute:
  # [...]

    def __set__(self, instance, value):
      instance._population = list(value)

    def __populate__(self, instance, value, unique_list=False):
        print("We're referenced in", value.get_node_name())
      if (
          value.get_node_name().endswith(".square") and
          (not unique_list or value not in instance._population)
        ):
            instance._population.append(value)
      else:
        print("We only store referrers coming from a .square configuration attribute")

  # [...]

  @config.node
  class Element:
    container = config.ref(container_ref, populate="elements", pop_unique=False)


Type validation
===============

Configuration types convert given configuration values. Values incompatible with the type
are rejected and the user is notified. The default type is ``str``.

Any callable that takes 1 argument can be used as a type handler. The :mod:`bsb:bsb.config.types`
module provides extra functionality such as validation of list and dictionaries and even
more complex combinations of types. Every configuration node itself can be used as a type.

.. warning::

    All of the members of the :mod:`bsb:bsb.config.types` module are factory methods: they need to
    be **called** in order to produce the type handler. Make sure that you use
    ``config.attr(type=types.any_())``, as opposed to ``config.attr(type=types.any_)``.

Examples
--------

.. code-block:: python

  from bsb import config, types

  @config.node
  class TestNode
    name = config.attr()

  @config.node
  class TypeNode
    # Default string
    some_string = config.attr()
    # Explicit & required string
    required_string = config.attr(type=str, required=True)
    # Float
    some_number = config.attr(type=float)
    # types.float / types.int
    bounded_float = config.attr(type=types.float(min=0.3, max=17.9))
    # Float, int or bool (attempted to cast in that order)
    combined = config.attr(type=types.or_(float, int, bool))
    # Another node
    my_node = config.attr(type=TestNode)
    # A list of floats
    list_of_numbers = config.attr(
      type=types.list(type=float)
    )
    # 3 floats
    list_of_numbers = config.attr(
      type=types.list(type=float, size=3)
    )
    # A scipy.stats distribution
    chi_distr = config.attr(type=types.distribution())
    # A python statement evaluation
    statement = config.attr(type=types.evaluation())
    # Create an np.ndarray with 3 elements out of a scalar
    expand = config.attr(
        type=types.scalar_expand(
            scalar_type=int,
            expand=lambda s: np.ones(3) * s
        )
    )
    # Create np.zeros of given shape
    zeros = config.attr(
        type=types.scalar_expand(
            scalar_type=types.list(type=int),
            expand=lambda s: np.zeros(s)
        )
    )
    # Anything
    any_ = config.attr(type=types.any_())
    # One of the following strings: "all", "some", "none"
    give_me = config.attr(type=types.in_(["all", "some", "none"]))
    # The answer to life, the universe, and everything else
    answer = config.attr(type=lambda x: 42)
    # You're either having cake or pie
    cake_or_pie = config.attr(type=lambda x: "cake" if bool(x) else "pie")

Type handlers
=============

The ``TypeHandler`` interface in the Brain Scaffold Builder (BSB) framework allows specification of advanced
type‑validation and conversion rules for configuration attributes. It shapes complex type‑handlers that require more
functionality than a simple function. Type handlers are *callables* with optional extra attributes used by the
configuration system.

``__call__(self, value)``
-------------------------

Convert the given configuration value to the desired Python type. Must raise ``TypeError`` (or subclass) when the value
is invalid.

``__name__(self)``
------------------

Return a display name for the type‑handler. This name is used in error messages and configuration diagnostics.

``__inv__(self, value)``
------------------------

Optional method to invert a converted value back to a representation suitable for serialization to configuration files.
Configuration files should be able to be loaded and saved again without unintentional changes to the content, and this
method allows complicated type handlers to create a bijective relationship between the serialized and runtime values.

Examples
--------

A type‑handler that accepts only even integers:

.. code-block:: python

    class EvenIntHandler(TypeHandler):
      def __call__(self, value):
          n = int(value)
          if n % 2 != 0:
              raise TypeError(f"{value!r} is not an even integer")
          return n

      def __name__(self):
          return "even integer"

A type‑handler that converts a colour name to an RGB tuple and supports inversion:

.. code-block:: python

  class ColourHandler(TypeHandler):
      def __call__(self, value):
          name = str(value).lower()
          if name == "red":
              return (255, 0, 0)
          if name == "green":
              return (0, 255, 0)
          if name == "blue":
              return (0, 0, 255)
          raise TypeError(f"{value!r} is not a valid colour")

      def __inv__(self, rgb):
          if rgb == (255, 0, 0):
              return "red"
          if rgb == (0, 255, 0):
              return "green"
          if rgb == (0, 0, 255):
              return "blue"
          # fallback
          return None

      def __name__(self):
          return "colour"

Usage in a config node definition:

.. code-block:: python

  from bsb import config

  @config.node
  class MyComponent:
      favourite_colour = config.attr(type=ColourHandler(), required=True)
      even_count      = config.attr(type=EvenIntHandler(), default=0)