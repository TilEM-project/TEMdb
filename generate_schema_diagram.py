import inspect
import re
import sys
from enum import Enum as PyEnum
from pathlib import Path
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase

PROJECT_ROOT = Path(__file__).parent
DOCS_DIR = PROJECT_ROOT / "docs"
MODELS_DOCS_DIR = DOCS_DIR / "models"


sys.path.insert(0, str(PROJECT_ROOT / "packages/temdb/src"))

WORKFLOW_GROUPS = {
    "Preparation": {
        "SpecimenSQLModel",
        "BlockSQLModel",
        "CuttingSessionSQLModel",
        "SectionSQLModel",
    },
    "Imaging": {
        "SectionSQLModel",
        "ROISQLModel",
        "AcquisitionTaskSQLModel",
        "AcquisitionSQLModel",
        "TileSQLModel",
    },
}

EXCLUDE_FIELDS_FROM_ERD = {"id", "created_at", "updated_at", "version"}
EXCLUDE_FIELDS_FROM_DETAIL = {"id"}


def _display_name(model_name: str) -> str:
    if model_name.endswith("SQLModel"):
        model_name = model_name[: -len("SQLModel")]
    if model_name == "ROIS":
        return "ROI"
    return model_name


def _parse_type(field_type: type) -> str:
    origin = get_origin(field_type)
    args = get_args(field_type)
    if origin is Union and type(None) in args:
        inner_type = next(arg for arg in args if arg is not type(None))
        return _parse_type(inner_type)
    if origin in (list, set):
        if args:
            return f"{_parse_type(args[0])}[]"
        return "any[]"
    if hasattr(field_type, "__name__"):
        type_name = field_type.__name__
        if type_name == "str":
            return "string"
        if type_name == "int":
            return "int"
        if type_name == "float":
            return "float"
        if type_name == "bool":
            return "bool"
        if type_name == "datetime":
            return "datetime"
        if type_name in {"Dict", "dict"}:
            return "object"
        if type_name == "Any":
            return "any"
        if hasattr(field_type, "mro"):
            if any(base is PyEnum for base in field_type.mro()):
                return "enum"
            if any(base is BaseModel for base in field_type.mro()):
                return "object"
        return type_name
    fallback_type = re.sub(r"[\[\].,\'\s]", "", str(field_type))
    return (fallback_type[:20] + "...") if len(fallback_type) > 20 else fallback_type


def find_sqlmodel_models() -> list[type[DeclarativeBase]]:
    import temdb.server.sqlmodels as sqlmodels_module
    from temdb.server.sqlmodels import Base

    discovered_models: list[type[DeclarativeBase]] = []
    for _, obj in inspect.getmembers(sqlmodels_module):
        if inspect.isclass(obj) and issubclass(obj, Base) and obj is not Base and getattr(obj, "__tablename__", None):
            discovered_models.append(obj)
    return discovered_models


def _model_fields(model: type[DeclarativeBase]) -> dict[str, Any]:
    return {column.key: column for column in model.__mapper__.columns}


def generate_model_markdown_page(model: type[DeclarativeBase]) -> str:
    model_name = _display_name(model.__name__)
    markdown = f"# {model_name} Model\n\n"
    model_doc = inspect.getdoc(model)
    if model_doc:
        markdown += f"{model_doc}\n\n"
    markdown += "## Fields\n\n"
    markdown += "| Field Name | Type | Description |\n"
    markdown += "|------------|------|-------------|\n"
    fields = _model_fields(model)
    for field_name, column in fields.items():
        if field_name in EXCLUDE_FIELDS_FROM_DETAIL:
            continue
        field_type_hint = getattr(column.type, "python_type", None)
        mermaid_type = _parse_type(field_type_hint) if field_type_hint else "unknown"
        description = ""
        description = description.replace("|", "\\|")
        markdown += f"| `{field_name}` | {mermaid_type} | {description} |\n"
    return markdown


def generate_erd_markdown(all_models: list[type[DeclarativeBase]], core_group_models: set[str]) -> str:
    all_model_map = {m.__name__: m for m in all_models}
    models_in_diagram = {name for name in core_group_models if name in all_model_map}

    class_definitions = []
    for model_name in sorted(models_in_diagram):
        model = all_model_map[model_name]
        class_def = f"    {model_name} {{\n"
        fields = _model_fields(model)
        for field_name, column in fields.items():
            if field_name in EXCLUDE_FIELDS_FROM_ERD:
                continue
            field_type_hint = getattr(column.type, "python_type", None)
            mermaid_type = _parse_type(field_type_hint) if field_type_hint else "unknown"
            class_def += f"        {mermaid_type} {field_name}\n"
        class_def += "    }"
        class_definitions.append(class_def)

    mermaid_string = "erDiagram\n"
    mermaid_string += "    direction LR\n"
    mermaid_string += "\n".join(class_definitions)
    mermaid_string += "\n"
    return f"```mermaid\n{mermaid_string}```"


def main():
    all_models = find_sqlmodel_models()
    if not all_models:
        print("No SQLAlchemy models found. Exiting.")
        return

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    for group_name, core_models_set in WORKFLOW_GROUPS.items():
        group_erd_content = generate_erd_markdown(all_models, core_models_set)
        group_erd_filename = DOCS_DIR / f"schema_{group_name}_erd.md"
        with open(group_erd_filename, "w") as f:
            f.write(f"# {group_name} Workflow Schema.\n\n{group_erd_content}")

    MODELS_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    for model in all_models:
        model_page_content = generate_model_markdown_page(model)
        output_path = MODELS_DOCS_DIR / f"{_display_name(model.__name__)}.md"
        with open(output_path, "w") as f:
            f.write(model_page_content)


if __name__ == "__main__":
    main()
