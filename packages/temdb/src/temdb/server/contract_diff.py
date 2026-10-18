from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class Change:
    bump: str
    where: str
    what: str


def rank(bump: str) -> int:
    return ("none", "patch", "minor", "major").index(bump)


def required_bump(changes: list[Change]) -> str:
    """The largest bump among `changes`, or "none" if there are no changes."""
    return max((c.bump for c in changes), key=rank, default="none")


def compare(old_spec: dict, new_spec: dict) -> list[Change]:
    """Every difference between the specs, most severe first."""
    old_ops, new_ops = _operations(old_spec), _operations(new_spec)
    changes = [Change("major", op, "operation removed") for op in old_ops.keys() - new_ops.keys()]
    changes += [Change("minor", op, "operation added") for op in new_ops.keys() - old_ops.keys()]
    for op in old_ops.keys() & new_ops.keys():
        changes += _compare_operation(old_ops[op], new_ops[op], op)
    if not changes:
        changes += _compare_unclassified(old_ops, new_ops)
    return sorted(changes, key=lambda c: (-rank(c.bump), c.where))


def _compare_unclassified(old_ops: dict, new_ops: dict) -> list[Change]:
    """Differences no rule above recognised: wording-only is a patch, anything else is treated as major."""
    if old_ops == new_ops:
        return []
    if _without_wording(old_ops) != _without_wording(new_ops):
        return [Change("major", "spec", "changed in a way these rules do not classify")]
    return [Change("patch", "spec", "descriptions or titles changed")]


def _compare_operation(old: dict, new: dict, where: str) -> Iterator[Change]:
    yield from _compare_parameters(old, new, where)
    yield from _compare_request_body(old, new, where)
    yield from _compare_responses(old, new, where)


def _compare_parameters(old: dict, new: dict, where: str) -> Iterator[Change]:
    old_params = {(p["in"], p["name"]): p for p in old.get("parameters", [])}
    new_params = {(p["in"], p["name"]): p for p in new.get("parameters", [])}
    for location, name in old_params.keys() - new_params.keys():
        yield Change("major", f"{where} {location} {name}", "parameter removed")
    for location, name in new_params.keys() - old_params.keys():
        required = new_params[location, name].get("required", False)
        what = "new required parameter" if required else "parameter added"
        yield Change("major" if required else "minor", f"{where} {location} {name}", what)
    for key in old_params.keys() & new_params.keys():
        location, name = key
        old_param, new_param = old_params[key], new_params[key]
        if new_param.get("required") and not old_param.get("required"):
            yield Change("major", f"{where} {location} {name}", "parameter now required")
        old_schema, new_schema = old_param.get("schema", {}), new_param.get("schema", {})
        yield from _compare_schema(old_schema, new_schema, "request", f"{where} {name}")


def _compare_request_body(old: dict, new: dict, where: str) -> Iterator[Change]:
    where = f"{where} body"
    old_body, new_body = old.get("requestBody"), new.get("requestBody")
    old_schema, new_schema = _json_schema(old_body), _json_schema(new_body)
    if old_schema is not None and new_schema is not None:
        yield from _compare_schema(old_schema, new_schema, "request", where)
    elif new_schema is not None and old_body is None:
        yield Change("major", where, "now takes a body")
    elif old_schema is not None and new_body is None:
        yield Change("major", where, "no longer takes a body")
    if (new_body or {}).get("required") and not (old_body or {}).get("required"):
        yield Change("major", where, "now required")


def _compare_responses(old: dict, new: dict, where: str) -> Iterator[Change]:
    new_responses = new.get("responses", {})
    for code, old_response in old.get("responses", {}).items():
        if not code.startswith("2"):
            continue
        if code not in new_responses:
            yield Change("major", f"{where} {code}", "response removed")
            continue
        old_schema, new_schema = _json_schema(old_response), _json_schema(new_responses[code])
        if old_schema is not None and new_schema is not None:
            yield from _compare_schema(old_schema, new_schema, "response", f"{where} {code}")


def _compare_schema(old: dict, new: dict, direction: str, where: str) -> Iterator[Change]:
    """`direction` is "request" or "response"; it decides which changes break a client."""
    old_nullable, old_options = _variants(old)
    new_nullable, new_options = _variants(new)
    yield from _compare_nullability(old_nullable, new_nullable, direction, where)
    if sorted(map(_kind, old_options)) != sorted(map(_kind, new_options)):
        yield Change("major", where, "type changed")
        return
    if len(old_options) != 1:
        return
    old, new = old_options[0], new_options[0]
    yield from _compare_constraints(old, new, direction, where)
    match _kind(old):
        case "enum":
            yield from _compare_enum(old, new, direction, where)
        case "object":
            yield from _compare_object(old, new, direction, where)
        case "array":
            yield from _compare_schema(old.get("items", {}), new.get("items", {}), direction, f"{where}[]")


def _compare_nullability(old_nullable: bool, new_nullable: bool, direction: str, where: str) -> Iterator[Change]:
    if direction == "response" and new_nullable and not old_nullable:
        yield Change("major", where, "may now be null")
    if direction == "request" and old_nullable and not new_nullable:
        yield Change("major", where, "no longer accepts null")
    if direction == "request" and new_nullable and not old_nullable:
        yield Change("minor", where, "now accepts null")


def _compare_constraints(old: dict, new: dict, direction: str, where: str) -> Iterator[Change]:
    """A request is broken by tighter limits, a response by looser ones; a changed pattern breaks both."""
    breaking = "tightened" if direction == "request" else "loosened"
    for keyword, how in _constraint_changes(old, new):
        yield Change(
            "major" if how in ("changed", breaking) else "minor",
            where,
            f"{keyword} {how}",
        )


def _constraint_changes(old: dict, new: dict) -> Iterator[tuple[str, str]]:
    """(keyword, tightened | loosened | changed) for each validation keyword whose value differs."""
    upper_bounds = ("maxLength", "maxItems", "maximum", "exclusiveMaximum")
    lower_bounds = ("minLength", "minItems", "minimum", "exclusiveMinimum")
    for keyword in (*upper_bounds, *lower_bounds, "pattern", "multipleOf"):
        before, after = old.get(keyword), new.get(keyword)
        if before == after:
            continue
        if before is None:
            yield keyword, "tightened"
        elif after is None:
            yield keyword, "loosened"
        elif keyword in upper_bounds:
            yield keyword, "tightened" if after < before else "loosened"
        elif keyword in lower_bounds:
            yield keyword, "tightened" if after > before else "loosened"
        else:
            yield keyword, "changed"


def _compare_enum(old: dict, new: dict, direction: str, where: str) -> Iterator[Change]:
    old_values, new_values = _enum_values(old), _enum_values(new)
    added = sorted(map(str, new_values - old_values))
    removed = sorted(map(str, old_values - new_values))
    if direction == "response" and added:
        yield Change("major", where, f"new values {added}")
    if direction == "request" and removed:
        yield Change("major", where, f"values no longer accepted {removed}")
    if direction == "request" and added:
        yield Change("minor", where, f"new values {added}")


def _compare_object(old: dict, new: dict, direction: str, where: str) -> Iterator[Change]:
    old_props, new_props = old.get("properties", {}), new.get("properties", {})
    old_required, new_required = set(old.get("required", [])), set(new.get("required", []))
    for name in old_props.keys() - new_props.keys():
        yield Change("major", f"{where}.{name}", "removed")
    for name in new_props.keys() - old_props.keys():
        if direction == "request" and name in new_required:
            yield Change("major", f"{where}.{name}", "new required field")
        elif direction == "response" and old.get("additionalProperties") is False:
            yield Change("major", f"{where}.{name}", "added where clients reject unknown fields")
        else:
            yield Change("minor", f"{where}.{name}", "added")
    for name in old_props.keys() & new_props.keys():
        if direction == "response" and name in old_required and name not in new_required:
            yield Change("major", f"{where}.{name}", "may now be missing")
        if direction == "request" and name in new_required and name not in old_required:
            yield Change("major", f"{where}.{name}", "now required")
        yield from _compare_schema(old_props[name], new_props[name], direction, f"{where}.{name}")
    old_extra, new_extra = old.get("additionalProperties"), new.get("additionalProperties")
    if isinstance(old_extra, dict) and isinstance(new_extra, dict):
        yield from _compare_schema(old_extra, new_extra, direction, f"{where}.*")


def _variants(schema: dict) -> tuple[bool, list[dict]]:
    """(nullable, the non-null alternatives) of a schema."""
    options = schema.get("anyOf") or schema.get("oneOf") or [schema]
    return any(o.get("type") == "null" for o in options), [o for o in options if o.get("type") != "null"]


def _kind(schema: dict) -> str:
    if "enum" in schema or "const" in schema:
        return "enum"
    if "properties" in schema or "additionalProperties" in schema:
        return "object"
    return str(schema.get("type", "any"))


def _enum_values(schema: dict) -> set:
    return set(schema.get("enum", [schema.get("const")]))


def _json_schema(holder: dict | None) -> dict | None:
    """The application/json schema of a requestBody or response, if it has one."""
    return (holder or {}).get("content", {}).get("application/json", {}).get("schema")


def _operations(spec: dict) -> dict[str, dict]:
    """Every operation keyed by "METHOD /path", with its schema $refs inlined."""
    components = spec.get("components", {}).get("schemas", {})
    return {
        f"{method.upper()} {path}": _resolve(operation, components)
        for path, item in spec.get("paths", {}).items()
        for method, operation in item.items()
    }


def _resolve(schema, components: dict, seen: frozenset = frozenset()):
    """Inline every $ref so renamed components with the same shape compare equal; a cycle stays a $ref."""
    if isinstance(schema, list):
        return [_resolve(item, components, seen) for item in schema]
    if not isinstance(schema, dict):
        return schema
    ref = schema.get("$ref")
    if ref is not None:
        name = ref.split("/")[-1]
        return {"$ref": name} if name in seen else _resolve(components[name], components, seen | {name})
    return {key: _resolve(value, components, seen) for key, value in schema.items()}


def _without_wording(node, in_properties: bool = False):
    """The node without descriptions, titles and examples.

    Keys directly under `properties` are field names, not wording, so they are kept.
    """
    if isinstance(node, list):
        return [_without_wording(item) for item in node]
    if not isinstance(node, dict):
        return node
    return {
        key: _without_wording(value, key == "properties")
        for key, value in node.items()
        if in_properties or key not in ("description", "title", "summary", "example", "examples")
    }
