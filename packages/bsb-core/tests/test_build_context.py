import unittest

from bsb import config
from bsb.config import (
    BuildContext,
    build_context,
    get_config_build_context,
    set_config_build_context,
)


class TestBuildContextPrimitive(unittest.TestCase):
    def test_get_outside_build_returns_none(self):
        self.assertIsNone(get_config_build_context())

    def test_set_and_reset_via_token(self):
        ctx = BuildContext()
        token = set_config_build_context(ctx)
        try:
            self.assertIs(get_config_build_context(), ctx)
        finally:
            # The ContextVar.reset call lives on the token, mirroring stdlib usage.
            from bsb.config._build_context import _build_context_var

            _build_context_var.reset(token)
        self.assertIsNone(get_config_build_context())

    def test_build_context_manager_clears_on_exit(self):
        with build_context() as ctx:
            self.assertIs(get_config_build_context(), ctx)
        self.assertIsNone(get_config_build_context())

    def test_build_context_manager_clears_on_exception(self):
        with self.assertRaises(RuntimeError):
            with build_context():
                self.assertIsNotNone(get_config_build_context())
                raise RuntimeError("boom")
        self.assertIsNone(get_config_build_context())

    def test_namespace_auto_vivifies(self):
        ctx = BuildContext()
        ctx.bsb_nest.kernel = "proxy-sentinel"
        self.assertEqual(ctx.bsb_nest.kernel, "proxy-sentinel")

    def test_cleanups_run_in_lifo_order(self):
        order = []
        with build_context() as ctx:
            ctx.add_cleanup(lambda: order.append("first"))
            ctx.add_cleanup(lambda: order.append("second"))
        self.assertEqual(order, ["second", "first"])

    def test_cleanup_failure_does_not_block_others(self):
        order = []

        def boom():
            raise RuntimeError("cleanup failure")

        with build_context() as ctx:
            ctx.add_cleanup(lambda: order.append("ran"))
            ctx.add_cleanup(boom)
        self.assertEqual(order, ["ran"])

    def test_cleanups_run_on_exception(self):
        order = []
        with self.assertRaises(RuntimeError):
            with build_context() as ctx:
                ctx.add_cleanup(lambda: order.append("ran"))
                raise RuntimeError("boom")
        self.assertEqual(order, ["ran"])


class TestBuildContextDuringConfigBuild(unittest.TestCase):
    """Verify the root configuration build activates the context."""

    def test_context_active_during_required_checker(self):
        seen = []

        def checker(kwargs):
            seen.append(get_config_build_context())
            return False

        @config.node
        class Inner:
            value = config.attr(type=int, required=checker, default=1)

        @config.root
        class Root:
            inner = config.attr(type=Inner, default=dict, call_default=True)

        Root({"inner": {"value": 5}})

        self.assertEqual(len(seen), 1)
        self.assertIsInstance(seen[0], BuildContext)
        # After the root build returns, the context has been cleared.
        self.assertIsNone(get_config_build_context())


if __name__ == "__main__":
    unittest.main()
