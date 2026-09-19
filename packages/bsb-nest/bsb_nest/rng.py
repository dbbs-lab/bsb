from bsb import RngSettings, config, types


@config.node
class NestRngSettings(RngSettings, classmap_entry="nest"):
    """
    The master seed NEST's kernel is handed.

    NEST is not drawn from: it takes one number and makes its own per virtual
    process and per rank streams out of it. So there is nothing to configure here
    beyond which number it starts from, and leaving that unset derives one from the
    network's root seed and writes it back, like any other node in the block.
    """

    seed: int = config.attr(type=types.int(min=1), required=False)
    """
    Master seed handed to the kernel. NEST rejects zero, so this is narrower than the
    block's own seed. Left unset, it is derived from the root seed and written back.
    """


def kernel_seed(consumer, key=()) -> int:
    """
    A seed NEST's kernel accepts, out of whatever a consumer is seeded from.

    :param consumer: The :class:`~bsb.rng.RngSettingsConsumer` being seeded.
    :param key: What the seed is for, used only when it names no settings entry.
    :returns: A positive 32 bit integer.
    """
    # A derived seed is any 32 bit value and NEST rejects zero. A seed written in
    # the configuration is handed on untouched, so what is pinned is what is used.
    return consumer.derive_seed(key) or 1


__all__ = ["NestRngSettings", "kernel_seed"]
