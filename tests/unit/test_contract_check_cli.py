import json

import pytest

import temdb.server.main
from temdb.server.cli import contract_check_main


def baseline_with_an_extra_response_field(app, path):
    spec = json.loads(json.dumps(app.openapi()))
    specimen = spec["components"]["schemas"]["SpecimenResponse"]
    specimen["properties"]["legacy_field"] = {"type": "string"}
    specimen["required"].append("legacy_field")
    path.write_text(json.dumps({"version": "3.0.0", "spec": spec}))


@pytest.fixture(autouse=True)
def shared_app(app, monkeypatch):
    monkeypatch.setattr(temdb.server.main, "create_app", lambda: app)


def test_a_bump_below_what_the_changes_need_fails(app, tmp_path, capsys):
    baseline = tmp_path / "released.json"
    baseline_with_an_extra_response_field(app, baseline)
    with pytest.raises(SystemExit) as stopped:
        contract_check_main(["--baseline", str(baseline), "--bump", "minor"])
    assert stopped.value.code == 1
    assert "major" in capsys.readouterr().out


def test_a_big_enough_bump_passes(app, tmp_path):
    baseline = tmp_path / "released.json"
    baseline_with_an_extra_response_field(app, baseline)
    contract_check_main(["--baseline", str(baseline), "--bump", "major"])


def test_record_writes_the_current_contract_with_the_models_version(app, tmp_path):
    baseline = tmp_path / "released.json"
    contract_check_main(["--baseline", str(baseline), "--record"])
    recorded = json.loads(baseline.read_text())
    assert recorded["spec"] == json.loads(json.dumps(app.openapi()))
    contract_check_main(["--baseline", str(baseline), "--bump", "patch"])
