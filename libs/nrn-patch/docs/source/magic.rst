Magic methods
=============

\_\_neuron\_\_
--------------

*Get the object's NEURON pointer*

Whenever an object with this method present is sent to the NEURON HOC interpreter, the
result of this method is passed instead. This allows Python methods to encapsulate NEURON
pointers transparently

\_\_netcon\_\_
--------------

*Get the object's NetCon pointer*

Whenever an object with this method present is used in a :meth:`NetCon
<.interpreter.PythonHocInterpreter.NetCon>` call, the result of this method is passed
instead. The connection is stored on the original object. This allows to simplify the
calls to NetCon, or to add more elegant default behavior. For example inserting a
connection on a section might connect it to a random segment and you'd be able to use
``p.NetCon(section, synapse)``.
