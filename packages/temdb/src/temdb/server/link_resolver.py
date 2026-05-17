from typing import Sequence

from beanie import Document
from beanie.odm.fields import PydanticObjectId

Registry = dict[str, dict[PydanticObjectId, Document]]


async def resolve_links(
    docs: Document | Sequence[Document] | None,
    refs: Sequence[tuple[str, type[Document]]],
) -> Registry:
    """Resolve ObjectId reference fields with one $in query per (field, target).

    Args:
        docs: Single doc, list of docs, or None.
        refs: List of (field_name, target_document_class) tuples. The field on
            each doc must be a PydanticObjectId, list[PydanticObjectId], or None.

    Returns:
        registry[field_name][object_id] -> target Document instance.
        Missing references are simply absent from the registry — callers
        decide whether that is a 404 or a nullable response field.
    """
    if docs is None:
        return {field: {} for field, _ in refs}
    if isinstance(docs, Document):
        docs = [docs]

    registry: Registry = {}
    for field_name, target_cls in refs:
        ids: set[PydanticObjectId] = set()
        for d in docs:
            v = getattr(d, field_name, None)
            if v is None:
                continue
            if isinstance(v, list):
                ids.update(x for x in v if x is not None)
            else:
                ids.add(v)
        if not ids:
            registry[field_name] = {}
            continue
        results = await target_cls.find({"_id": {"$in": list(ids)}}).to_list()
        registry[field_name] = {r.id: r for r in results}
    return registry
