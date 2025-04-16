import importlib
import pathlib


def get_test_config_module(name: str):
    try:
        return importlib.import_module(f".{name}", package=get_test_config.__module__)
    except Exception as e:
        raise ValueError(f"'{name}' is not a known test configuration.") from e


def get_test_config_tree(name: str):
    module = get_test_config_module(name)
    return module.tree


def get_test_config(name: str):
    from bsb.config import Configuration

    tree = get_test_config_tree(name)
    return Configuration(tree)


def get_test_configs(available_plugins=None):
    return {
        n: get_test_config(n)
        for n in list_test_configs(available_plugins=available_plugins)
    }


def list_test_configs(available_plugins=None):
    available_plugins = available_plugins or []
    config_names = [
        p.stem
        for p in pathlib.Path(__file__).parent.glob("*.py")
        if p.name != "__init__.py"
    ]
    return [
        name
        for name in config_names
        # Include the test config only if all the required plugins are available
        if (
            not (req := getattr(get_test_config_module(name), "required_plugins", None))
            or all(p in available_plugins for p in req)
        )
    ]
