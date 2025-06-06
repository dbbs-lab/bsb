"""
Utilities for comparing NEURON simulator versions.

This module provides a `NeuronVersion` class that extends `packaging.version.Version`
and automatically supports comparisons with plain version strings.

Example:
    >>> from patch.version import NeuronVersion
    >>> nv = NeuronVersion()
    >>> print(nv.full_version)  # e.g., '9.0a-1422-g8b0b34549'
    >>> print(nv.semantic_version)  # e.g., '9.0a'
    >>> if nv >= "9.0":
    ...     print("NEURON version is at least 9.0")

Requirements:
    - The `neuron` Python module must be installed.
    - The `packaging` library is used for version parsing.
"""

import packaging.version


class NeuronVersion(packaging.version.Version):
    """
    A subclass of `packaging.version.Version` that supports direct comparison
    with version strings, and exposes NEURON's full and semantic version strings.

    On instantiation, it reads the installed NEURON version and parses the semantic
    part for comparison.

    :param version: Optional semantic version string. If not provided, reads from
       installed neuron.

    :type version: str, optional
    """

    def __init__(self, version: str = None):
        if version is None:
            version = self._get_semantic_version_from_neuron()
        super().__init__(version)

    @staticmethod
    def _get_full_version_from_neuron() -> str:
        import neuron

        version = neuron.__version__
        if str(version) == "neuron.__version__":
            # Mocked attribute, replace with v0
            return "0.0.0-mocked"
        return version

    @classmethod
    def _get_semantic_version_from_neuron(cls) -> str:
        full_version = cls._get_full_version_from_neuron()
        return full_version.split("-")[0]

    @property
    def full_version(self) -> str:
        """
        The full NEURON version string (including build metadata).

        :return: The full version string from the neuron module.
        :rtype: str
        """
        return self._get_full_version_from_neuron()

    @property
    def semantic_version(self) -> str:
        """
        The semantic NEURON version string used for comparisons.

        :return: The semantic version string (e.g., '9.0a').
        :rtype: str
        """
        return self._get_semantic_version_from_neuron()

    @staticmethod
    def _coerce_other(other):
        if isinstance(other, str):
            return packaging.version.Version(other)
        return other

    def __lt__(self, other):
        return super().__lt__(self._coerce_other(other))

    def __le__(self, other):
        return super().__le__(self._coerce_other(other))

    def __gt__(self, other):
        return super().__gt__(self._coerce_other(other))

    def __ge__(self, other):
        return super().__ge__(self._coerce_other(other))


def get_neuron_version() -> NeuronVersion:
    """
    Retrieve the semantic version of the installed NEURON module as
    a `NeuronVersion` object.

    :return: A `NeuronVersion` object representing the current NEURON version.
    :rtype: NeuronVersion
    """
    return NeuronVersion()
