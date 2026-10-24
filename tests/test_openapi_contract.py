import json
from pathlib import Path

import pytest


def schema_named(spec: dict, ref: str) -> dict:
    return spec["components"]["schemas"][ref.split("/")[-1]]


def operation_schema_refs(spec: dict, method: str, path: str, part: str) -> str:
    operation = spec["paths"][path][method]
    if part == "request":
        return operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    return schema.get("items", schema)["$ref"]


def test_committed_spec_matches_the_app(app):
    committed = json.loads((Path(__file__).resolve().parents[1] / "openapi.json").read_text())
    current = json.loads(json.dumps(app.openapi()))
    assert committed == current, "API changed: run `uv run temdb-openapi > openapi.json` and commit openapi.json"


def test_a_schema_allows_unknown_fields_exactly_when_validation_ignores_them(app):
    spec = app.openapi()
    run = schema_named(spec, operation_schema_refs(spec, "get", "/api/v2/acquisitions/{acquisition_id}", "response"))
    assert "additionalProperties" not in run
    assert spec["components"]["schemas"]["HardwareParams"]["additionalProperties"] is False
    patch = schema_named(spec, operation_schema_refs(spec, "patch", "/api/v2/acquisitions/{acquisition_id}", "request"))
    assert patch["additionalProperties"] is False


def test_a_version_bump_rewrites_the_spec_version():
    tomllib = pytest.importorskip("tomllib")
    root = Path(__file__).resolve().parents[1]
    config = tomllib.loads((root / ".bumpversion.toml").read_text())["tool"]["bumpversion"]
    entries = [entry for entry in config["files"] if entry["filename"] == "openapi.json"]
    assert len(entries) == 1
    search = entries[0]["search"].format(current_version=config["current_version"])
    assert (root / "openapi.json").read_text().count(search) == 1
