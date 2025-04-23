# filename: generate_schema_diagram.py

import importlib
import inspect
import pkgutil
import re
import sys
from enum import Enum as PyEnum
from pathlib import Path
from typing import (
    ForwardRef,
    List,
    Optional,
    Set,
    Type,
    Union,
    get_args,
    get_origin,
)

from pydantic import BaseModel
from beanie import Document, Link

PROJECT_ROOT = Path(__file__).parent 
MODELS_DIR_REL = "temdb/models/v2"
DOCS_DIR = PROJECT_ROOT / "docs" 
MODELS_DOCS_DIR = DOCS_DIR / "models"



sys.path.insert(0, str(PROJECT_ROOT))

WORKFLOW_GROUPS = {
    "Preparation": {
        "Specimen",
        "Block",
        "CuttingSession",
        "Section",
    },
    "Imaging": {
        "Section",
        "ROI",
        "AcquisitionTask",
        "Acquisition",
        "Tile",
    },
   
}

EXCLUDE_FIELDS_FROM_ERD = {
    "id",
    "revision_id",
    "created_at",
    "updated_at",
    "version",
}
EXCLUDE_FIELDS_FROM_DETAIL = {"id", "revision_id"}


def _parse_type(field_type: Type) -> tuple[str, Optional[str], bool]:
    origin = get_origin(field_type)
    args = get_args(field_type)
    target_model_name = None
    is_link_list = False
    if origin is Union and type(None) in args:
        inner_type = next(arg for arg in args if arg is not type(None))
        return _parse_type(inner_type)
    collection_suffix = ""
    is_list_or_set = False
    if origin in (list, List):
        is_list_or_set = True
        collection_suffix = "[]"
    elif origin in (set, Set):
        is_list_or_set = True
        collection_suffix = "[]"
    if is_list_or_set:
        if args:
            inner_type = args[0]
            inner_mermaid_type, inner_target_model, _ = _parse_type(inner_type)
            target_model_name = inner_target_model
            is_link_list = bool(target_model_name)
            mermaid_type = f"{inner_mermaid_type}{collection_suffix}"
            return mermaid_type, target_model_name, is_link_list
        else:
            return "any[]", None, False
    if origin is Link:
        if args:
            target_model = args[0]
            if isinstance(target_model, (str, ForwardRef)):
                target_model_name = (
                    str(target_model).split(".")[-1].replace("'", "").replace('"', "")
                )
            elif hasattr(target_model, "__name__"):
                target_model_name = target_model.__name__
            else:
                target_model_name = "UnknownLinkTarget"
            mermaid_type = target_model_name
            return mermaid_type, target_model_name, False
        else:
            return "Unknown", "Unknown", False
    if hasattr(field_type, "__name__"):
        type_name = field_type.__name__
        if type_name in ["str"]:
            return "string", None, False
        if type_name in ["int"]:
            return "int", None, False
        if type_name in ["float"]:
            return "float", None, False
        if type_name in ["bool"]:
            return "bool", None, False
        if type_name in ["datetime"]:
            return "datetime", None, False
        if type_name in ["Dict", "dict"]:
            return "object", None, False
        if type_name in ["Any"]:
            return "any", None, False
        if type_name in ["AnyUrl"]:
            return "url", None, False
        if type_name in ["UUID", "uuid"]:
            return "uuid", None, False
        if type_name in ["ObjectId", "PydanticObjectId", "BsonObjectId"]:
            return "objectid", None, False
        if hasattr(field_type, "mro"):
            if any(base is PyEnum for base in field_type.mro()):
                return "enum", None, False
            if any(base is BaseModel for base in field_type.mro()) and not any(
                base is Document for base in field_type.mro()
            ):
                return "object", None, False
        return type_name, None, False
    fallback_type = re.sub(r"[\[\].,\'\s]", "", str(field_type))
    fallback_type = (
        (fallback_type[:20] + "...") if len(fallback_type) > 20 else fallback_type
    )
    return fallback_type, None, False


def find_beanie_models(base_path: Path, models_rel_path: str) -> List[Type[Document]]:
    models_abs_path = base_path / models_rel_path
    models_package = models_rel_path.replace("/", ".")
    discovered_models = []
    print(f"Searching for models in: {models_abs_path}")
    print(f"Using package prefix: {models_package}")
    for _, module_name, _ in pkgutil.walk_packages([str(models_abs_path)]):
        if module_name in ["base", "enum_schemas"]:
            print(f"  Skipping module: {module_name}")
            continue
        try:
            full_module_name = f"{models_package}.{module_name}"
            print(f"  Importing module: {full_module_name}")
            module = importlib.import_module(full_module_name)
            for name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, Document)
                    and obj is not Document
                ):
                    if obj.__module__ == full_module_name:
                        print(f"    Found Beanie model: {name}")
                        discovered_models.append(obj)
        except ImportError as e:
            print(f"    Error importing {full_module_name}: {e}")
        except Exception as e:
            print(f"    Unexpected error processing {full_module_name}: {e}")
    return discovered_models


def generate_model_markdown_page(model: Type[Document]) -> str:
    model_name = model.__name__
    markdown = f"# {model_name} Model\n\n"
    model_doc = inspect.getdoc(model)
    if model_doc:
        markdown += f"{model_doc}\n\n"
    markdown += "## Fields\n\n"
    markdown += "| Field Name | Type | Description |\n"
    markdown += "|------------|------|-------------|\n"
    fields = getattr(model, "model_fields", {})
    for field_name, field_info in fields.items():
        if field_name in EXCLUDE_FIELDS_FROM_DETAIL:
            continue
        field_type_hint = getattr(
            field_info, "annotation", getattr(field_info, "outer_type_", None)
        )
        if field_type_hint is None:
            mermaid_type, target_link_model, _ = "unknown", None, False
        else:
            mermaid_type, target_link_model, _ = _parse_type(field_type_hint)
        display_type = mermaid_type
        if target_link_model:
            target_file_rel_path = f"{target_link_model}.md"
            display_type = f"[{target_link_model}]({target_file_rel_path})"
            if "[]" in mermaid_type:
                display_type += "[]"
        description = (
            getattr(
                field_info,
                "description",
                getattr(getattr(field_info, "field_info", None), "description", None),
            )
            or ""
        )
        description = description.replace("|", "\\|")
        markdown += f"| `{field_name}` | {display_type} | {description} |\n"
    return markdown


def generate_erd_markdown(
    all_models: List[Type[Document]], core_group_models: Set[str]
) -> str:
    """
    Generates a Mermaid ERD Markdown string for a specific group of models,
    including directly linked models for context.
    """
    all_model_map = {m.__name__: m for m in all_models}
    core_models_in_group = {name for name in core_group_models if name in all_model_map}

    models_in_diagram = set(core_models_in_group)
    related_models_to_add = set()

    for model_name in core_models_in_group:
        model = all_model_map[model_name]
        fields = getattr(model, "model_fields",  {})
        for _, field_info in fields.items():
            field_type_hint = getattr(
                field_info, "annotation", getattr(field_info, "outer_type_", None)
            )
            if field_type_hint:
                _, target_link_model, _ = _parse_type(field_type_hint)
                if target_link_model and target_link_model in all_model_map:
                    related_models_to_add.add(target_link_model)

    for model in all_models:
        model_name = model.__name__
        if model_name in core_models_in_group:
            continue

        fields = getattr(model, "model_fields",  {})
        for _, field_info in fields.items():
            field_type_hint = getattr(
                field_info, "annotation", getattr(field_info, "outer_type_", None)
            )
            if field_type_hint:
                _, target_link_model, _ = _parse_type(field_type_hint)
                if target_link_model and target_link_model in core_models_in_group:
                    related_models_to_add.add(
                        model_name
                    ) 
                    break

    models_in_diagram.update(related_models_to_add)
    print(f"  Models included in this diagram: {sorted(list(models_in_diagram))}")

    class_definitions = []
    relationships = []

    for model_name in sorted(
        list(models_in_diagram)
    ):
        model = all_model_map[model_name]
        class_def = f"    {model_name} {{\n"
        fields = getattr(model, "model_fields", {})

        for field_name, field_info in fields.items():
            if field_name in EXCLUDE_FIELDS_FROM_ERD:
                continue

            field_type_hint = getattr(
                field_info, "annotation", getattr(field_info, "outer_type_", None)
            )
            if field_type_hint is None:
                mermaid_type, target_link_model, is_link_list = "unknown", None, False
            else:
                mermaid_type, target_link_model, is_link_list = _parse_type(
                    field_type_hint
                )

            description = (
                getattr(
                    field_info,
                    "description",
                    getattr(
                        getattr(field_info, "field_info", None), "description", None
                    ),
                )
                or ""
            )
            description = description.replace('"', "'")

            class_def += f"        {mermaid_type} {field_name}"
            if target_link_model:
                class_def += " FK"
            class_def += "\n"

            if target_link_model and target_link_model in models_in_diagram:
                source_model = model_name
                target_model = target_link_model
                if is_link_list:
                    cardinality_symbol = "}o--o{"  # M:N
                    relationship_string = f"    {source_model} {cardinality_symbol} {target_model} : {field_name}"
                else:
                    cardinality_symbol = "}o--||"  # M:1
                    relationship_string = f"    {target_model} {cardinality_symbol} {source_model} : {field_name}"
                relationships.append(relationship_string)

        class_def += "    }"
        class_definitions.append(class_def)

    mermaid_string = "erDiagram\n"
    mermaid_string += "    direction LR\n"
    mermaid_string += "\n".join(class_definitions)
    mermaid_string += "\n\n"
    mermaid_string += "\n".join(sorted(list(set(relationships))))
    mermaid_string += "\n"

    return f"```mermaid\n{mermaid_string}```"


def main():
    """Main function to generate grouped ERDs and individual model pages."""
    print("--- Starting Schema Documentation Generation ---")
    all_models = find_beanie_models(PROJECT_ROOT, MODELS_DIR_REL)
    if not all_models:
        print("No Beanie models found. Exiting.")
        return

    print("\n--- Generating Grouped ERD Diagrams ---")
    DOCS_DIR.mkdir(parents=True, exist_ok=True) 

    for group_name, core_models_set in WORKFLOW_GROUPS.items():
        print(f"\n--- Generating ERD for Group: {group_name} ---")
        group_erd_content = generate_erd_markdown(all_models, core_models_set)
        group_erd_filename = DOCS_DIR / f"schema_{group_name}_erd.md"
        print(f"--- Writing {group_name} ERD diagram to: {group_erd_filename} ---")
        with open(group_erd_filename, "w") as f:
            f.write(
                f"# {group_name} Workflow Schema.\n\n{group_erd_content}"
            )

    print("\n--- Generating Individual Model Pages ---")
    MODELS_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    models_to_document = [m for m in all_models if m.__name__ != "BaseDocument"]

    for model in models_to_document:
        model_name = model.__name__
        print(f"  Generating page for: {model_name}")
        model_page_content = generate_model_markdown_page(model)
        output_path = MODELS_DOCS_DIR / f"{model_name}.md"
        with open(output_path, "w") as f:
            f.write(model_page_content)
        print(f"    -> Saved to: {output_path}")

    print("\n--- Documentation Generation Complete ---")


if __name__ == "__main__":
    main()
