from bsb import ConfigurationError


def merged(model, *groups):
    """
    One mapping out of the notations a NEST model accepts.

    A model writes its parameters apart for the reader's sake, as constants beside
    computed ones, or as first class attributes beside both. They mean the same thing
    to the model, so they are handed on as one mapping and nothing downstream sees
    the seam.

    Naming a parameter in two of them has no reading that is not a mistake, so it is
    an error rather than one notation quietly winning.

    :param model: The model the parameters belong to, named in the error.
    :param groups: The mappings to merge, in the order they are written.
    :returns: Every parameter, keyed by the model parameter it sets.
    """
    merged = {}
    for group in groups:
        for name, param in group.items():
            if name in merged:
                raise ConfigurationError(
                    f"Parameter '{name}' of {model} is configured twice; "
                    "give it in one place only."
                )
            merged[name] = param
    return merged
