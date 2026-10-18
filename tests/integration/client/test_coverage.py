import importlib
import inspect
import pkgutil
import typing

import tests.integration.client as package
from temdb.client import TEMdbClient


def client_methods() -> list[str]:
    names = []
    for resource_name, prop in inspect.getmembers(TEMdbClient, lambda member: isinstance(member, property)):
        resource_class = typing.get_type_hints(prop.fget)["return"]
        names += [
            f"{resource_name}.{name}"
            for name, _ in inspect.getmembers(resource_class, inspect.iscoroutinefunction)
            if not name.startswith("_")
        ]
    return sorted(names)


def integration_test_names() -> set[str]:
    names = set()
    for module_info in pkgutil.iter_modules(package.__path__):
        if module_info.name.startswith("test_"):
            module = importlib.import_module(f"{package.__name__}.{module_info.name}")
            names |= {name for name, _ in inspect.getmembers(module, inspect.iscoroutinefunction)}
    return names


def test_discovery_finds_methods_on_every_resource():
    resources = {name for name, _ in inspect.getmembers(TEMdbClient, lambda member: isinstance(member, property))}
    assert resources
    assert {name.split(".")[0] for name in client_methods()} == resources


def test_every_client_method_has_an_integration_test():
    expected = {"test_" + name.replace(".", "_") for name in client_methods()}
    assert len(expected) == len(client_methods())
    assert sorted(expected - integration_test_names()) == []
