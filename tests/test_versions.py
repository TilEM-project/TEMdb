import json
import re
from pathlib import Path


def project_file(*parts: str) -> str:
    return Path(__file__).resolve().parents[1].joinpath(*parts).read_text()


def test_every_package_and_pin_is_at_the_released_version():
    """The client's /contract check compares temdb-models versions, so all three packages move together."""
    current = re.search(r'current_version = "([^"]+)"', project_file(".bumpversion.toml"))[1]
    for package in ("temdb", "temdb-models", "temdb-client"):
        pyproject = project_file("packages", package, "pyproject.toml")
        assert re.search(r'(?m)^version = "([^"]+)"', pyproject)[1] == current, package
        assert set(re.findall(r'"temdb-models==([^"]+)"', pyproject)) <= {current}, package


def test_app_reports_the_released_version(app):
    current = re.search(r'current_version = "([^"]+)"', project_file(".bumpversion.toml"))[1]
    assert app.openapi()["info"]["version"] == current


def test_released_contract_version_matches_label():
    released = json.loads(project_file("contract", "openapi.released.json"))
    assert released["spec"]["info"]["version"] == released["version"]
