import copy

import pytest

from temdb.server.contract_diff import compare, required_bump


def spec_with(request: dict | None = None, response: dict | None = None, params: list | None = None) -> dict:
    """One POST /things operation whose request and 200 response point at components Body and Out."""
    return {
        "openapi": "3.1.0",
        "info": {"title": "t", "version": "1"},
        "paths": {
            "/things": {
                "post": {
                    "parameters": params or [],
                    "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/Body"}}}},
                    "responses": {
                        "200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/Out"}}}}
                    },
                }
            }
        },
        "components": {
            "schemas": {
                "Body": request or {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
                "Out": response or {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]},
            }
        },
    }


def changed(spec: dict, edit) -> dict:
    new = copy.deepcopy(spec)
    edit(new)
    return new


def test_identical_specs_need_no_bump():
    assert required_bump(compare(spec_with(), spec_with())) == "none"


def test_wording_only_changes_need_a_patch():
    new = changed(spec_with(), lambda s: s["components"]["schemas"]["Out"].update(description="the thing"))
    assert required_bump(compare(spec_with(), new)) == "patch"


def test_a_new_operation_or_response_field_is_minor():
    new = changed(spec_with(), lambda s: s["paths"].update({"/other": {"get": {"responses": {"200": {}}}}}))
    assert required_bump(compare(spec_with(), new)) == "minor"
    new = changed(
        spec_with(), lambda s: s["components"]["schemas"]["Out"]["properties"].update(extra={"type": "string"})
    )
    assert required_bump(compare(spec_with(), new)) == "minor"


def test_a_new_field_in_a_response_object_that_rejects_unknown_fields_is_major():
    closed = {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]}
    old = spec_with(response={**closed, "additionalProperties": False})
    new = changed(old, lambda spec: spec["components"]["schemas"]["Out"]["properties"].update(tag={"type": "string"}))
    assert required_bump(compare(old, new)) == "major"


def test_a_new_optional_request_field_is_minor():
    new = changed(
        spec_with(), lambda s: s["components"]["schemas"]["Body"]["properties"].update(note={"type": "string"})
    )
    assert required_bump(compare(spec_with(), new)) == "minor"


@pytest.mark.parametrize(
    "edit",
    [
        pytest.param(lambda s: s["paths"].pop("/things"), id="operation removed"),
        pytest.param(lambda s: s["components"]["schemas"]["Out"]["properties"].pop("id"), id="response field removed"),
        pytest.param(lambda s: s["components"]["schemas"]["Out"]["required"].clear(), id="response field optional"),
        pytest.param(
            lambda s: s["components"]["schemas"]["Out"]["properties"].update(
                id={"anyOf": [{"type": "integer"}, {"type": "null"}]}
            ),
            id="response field nullable",
        ),
        pytest.param(
            lambda s: s["components"]["schemas"]["Out"]["properties"].update(id={"type": "string"}),
            id="response type changed",
        ),
        pytest.param(
            lambda s: s["components"]["schemas"]["Body"]["properties"].pop("name"), id="request field removed"
        ),
        pytest.param(
            lambda s: (
                s["components"]["schemas"]["Body"]["properties"].update(code={"type": "string"}),
                s["components"]["schemas"]["Body"]["required"].append("code"),
            ),
            id="new required request field",
        ),
        pytest.param(
            lambda s: s["paths"]["/things"]["post"]["parameters"].append(
                {"name": "q", "in": "query", "required": True, "schema": {"type": "string"}}
            ),
            id="new required query parameter",
        ),
    ],
)
def test_changes_that_break_an_existing_client_are_major(edit):
    assert required_bump(compare(spec_with(), changed(spec_with(), edit))) == "major"


def test_a_new_response_enum_value_is_major_and_a_new_request_enum_value_is_minor():
    base = spec_with(
        request={"type": "object", "properties": {"kind": {"enum": ["a"]}}, "required": []},
        response={"type": "object", "properties": {"state": {"enum": ["x"]}}, "required": ["state"]},
    )
    more_out = changed(base, lambda s: s["components"]["schemas"]["Out"]["properties"]["state"]["enum"].append("y"))
    more_in = changed(base, lambda s: s["components"]["schemas"]["Body"]["properties"]["kind"]["enum"].append("b"))
    assert required_bump(compare(base, more_out)) == "major"
    assert required_bump(compare(base, more_in)) == "minor"


def test_renaming_a_component_without_changing_its_shape_is_not_a_change():
    """FastAPI renames shared schemas (X -> X-Output); clients see the same shape."""

    def rename(s):
        s["components"]["schemas"]["Out-Output"] = s["components"]["schemas"].pop("Out")
        s["paths"]["/things"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"] = (
            "#/components/schemas/Out-Output"
        )

    assert required_bump(compare(spec_with(), changed(spec_with(), rename))) == "none"


def test_each_change_names_where_it_is():
    new = changed(spec_with(), lambda s: s["components"]["schemas"]["Out"]["properties"].pop("id"))
    [change] = compare(spec_with(), new)
    assert change.bump == "major"
    assert "POST /things" in change.where and "id" in change.where


def field_body(field: dict) -> dict:
    return {"type": "object", "properties": {"name": field}, "required": ["name"]}


@pytest.mark.parametrize(
    ("old", "new", "bump"),
    [
        ({"type": "string", "maxLength": 100}, {"type": "string", "maxLength": 50}, "major"),
        ({"type": "string", "maxLength": 50}, {"type": "string", "maxLength": 100}, "minor"),
        ({"type": "integer", "minimum": 0}, {"type": "integer", "minimum": 5}, "major"),
        ({"type": "string"}, {"type": "string", "pattern": "^a"}, "major"),
        ({"type": "string", "maxLength": 10}, {"type": "string"}, "minor"),
        ({"type": "string", "pattern": "^a"}, {"type": "string", "pattern": "^b"}, "major"),
    ],
)
def test_request_constraints_bump_by_what_they_do_to_a_sender(old, new, bump):
    """A tightened request constraint can refuse what a client sends; a loosened one cannot."""
    assert required_bump(compare(spec_with(request=field_body(old)), spec_with(request=field_body(new)))) == bump


def test_a_loosened_response_constraint_is_major():
    """A client may rely on a response bound, so widening it can break the client."""
    old, new = field_body({"type": "string", "maxLength": 10}), field_body({"type": "string", "maxLength": 20})
    assert required_bump(compare(spec_with(response=old), spec_with(response=new))) == "major"


def test_a_tightened_parameter_constraint_is_major():
    param = {"in": "query", "name": "limit", "required": False}
    old = spec_with(params=[{**param, "schema": {"type": "integer", "maximum": 1000}}])
    new = spec_with(params=[{**param, "schema": {"type": "integer", "maximum": 100}}])
    assert required_bump(compare(old, new)) == "major"


def test_a_removed_request_body_is_major():
    new = changed(spec_with(), lambda s: s["paths"]["/things"]["post"].pop("requestBody"))
    assert required_bump(compare(spec_with(), new)) == "major"


def test_a_request_body_becoming_required_is_major():
    new = changed(spec_with(), lambda s: s["paths"]["/things"]["post"]["requestBody"].update(required=True))
    assert required_bump(compare(spec_with(), new)) == "major"


def test_a_structural_change_the_rules_do_not_cover_is_major():

    def error_response(schema_type):
        return lambda s: s["paths"]["/things"]["post"]["responses"].update(
            {"422": {"content": {"application/json": {"schema": {"type": schema_type}}}}}
        )

    old = changed(spec_with(), error_response("object"))
    new = changed(spec_with(), error_response("array"))
    assert required_bump(compare(old, new)) == "major"


def test_a_wording_only_change_is_patch():
    new = changed(spec_with(), lambda s: s["components"]["schemas"]["Out"].update(description="The stored thing"))
    assert required_bump(compare(spec_with(), new)) == "patch"
