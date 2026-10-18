import json

import temdb.server.main
from temdb.server.cli import openapi_main


def test_openapi_command_prints_the_apps_spec(app, monkeypatch, capsys):
    monkeypatch.setattr(temdb.server.main, "create_app", lambda: app)
    openapi_main()
    assert json.loads(capsys.readouterr().out) == json.loads(json.dumps(app.openapi()))
