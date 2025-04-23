from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from beanie import Document
from pydantic import BaseModel, Field
from pymongo import ASCENDING, DESCENDING, IndexModel


class ReferencePoints(BaseModel):
    origin: Optional[Tuple[float, float, float]] = Field(
        None, description="Origin point (x, y, z)"
    )
    end: Optional[Tuple[float, float, float]] = Field(
        None, description="End point (x, y, z)"
    )
    ref: Optional[Tuple[float, float, float]] = Field(
        None, description="Reference point (x, y, z)"
    )


class Aperture(BaseModel):
    """Represents a single aperture or slot on a substrate (like a grid, or aperture on tape)"""

    uid: str = Field(
        ...,
        description="Unique identifier for this aperture within the substrate (e.g., from XML)",
    )
    index: int = Field(..., description="Sequential index of the aperture")
    centroid: Optional[Tuple[float, float, float]] = Field(
        None, description="Calculated centroid of the aperture (X, Y, Z)"
    )
    shape: Optional[str] = Field(
        None,
        description="Raw description of the aperture shape (e.g., 'Circle:{\"diameter\": 10.2}')",
    )
    shape_type: Optional[str] = None
    shape_params: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(
        None, description="Status of the aperture (e.g., available, used, damaged)"
    )
    tracking_uid: Optional[str] = Field(
        None,
        alias="tuid",
        description="Tracking UID from source if available (purpose may need clarification)",
    )  # TODO: review alias if source name differs


class SubstrateMetadata(BaseModel):
    name: Optional[str] = Field(None, description="User-defined name for the substrate")
    user: Optional[str] = Field(
        None, description="User associated with substrate creation/calibration"
    )
    created: Optional[datetime] = Field(
        None, description="Timestamp from source metadata 'created'"
    )
    calibrated: Optional[datetime] = Field(
        None, description="Timestamp from source metadata 'calibrated'"
    )
    extra: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dictionary for any other key-value metadata items",
    )


class SubstrateCreate(BaseModel):
    media_id: str = Field(
        ...,
        description="Primary unique identifier for this substrate (e.g., wafer ID, tape reel ID)",
    )
    media_type: str = Field(
        ..., description="Type of substrate (e.g., 'wafer', 'tape', 'stick', 'grid')"
    )
    uid: Optional[str] = Field(
        None,
        description="Overall unique identifier for the substrate instance (e.g., from XML uid)",
    )
    status: Optional[str] = Field(
        "new",
        description="Status of the entire substrate (e.g., new, in_use, full, retired, damaged)",
    )
    refpoint: Optional[ReferencePoints] = Field(
        None, description="Reference points in local substrate coordinates"
    )
    refpoint_world: Optional[ReferencePoints] = Field(
        None, description="Reference points mapped to world/stage coordinates"
    )
    source_path: Optional[str] = Field(
        None,
        description="Path or identifier of the source file defining this substrate (e.g., XML path)",
    )
    metadata: Optional[SubstrateMetadata] = Field(
        None, description="General metadata about the substrate"
    )
    apertures: Optional[List[Aperture]] = Field(
        None,
        description="List of apertures or slots defined on this substrate, if applicable",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(None)


class SubstrateUpdate(BaseModel):
    media_id: Optional[str] = Field(
        None,
        description="Primary unique identifier for this substrate (e.g., wafer ID, tape reel ID)",
    )
    media_type: Optional[str] = Field(
        None, description="Type of substrate (e.g., 'wafer', 'tape', 'stick', 'grid')"
    )
    uid: Optional[str] = Field(
        None,
        description="Overall unique identifier for the substrate instance (e.g., from XML uid)",
    )
    status: Optional[str] = Field(
        None,
        description="Status of the entire substrate (e.g., new, in_use, full, retired, damaged)",
    )
    refpoint: Optional[ReferencePoints] = Field(
        None, description="Reference points in local substrate coordinates"
    )
    refpoint_world: Optional[ReferencePoints] = Field(
        None, description="Reference points mapped to world/stage coordinates"
    )
    source_path: Optional[str] = Field(
        None,
        description="Path or identifier of the source file defining this substrate (e.g., XML path)",
    )
    metadata: Optional[SubstrateMetadata] = Field(
        None, description="General metadata about the substrate"
    )
    apertures: Optional[List[Aperture]] = Field(
        None,
        description="List of apertures or slots defined on this substrate, if applicable",
    )
    created_at: Optional[datetime] = Field(
        None, description="Timestamp when the substrate was created"
    )
    updated_at: Optional[datetime] = Field(
        None, description="Timestamp when the substrate was last updated"
    )


class Substrate(Document):
    media_id: str = Field(
        ...,
        description="Primary unique identifier for this substrate (e.g., wafer ID, tape reel ID)",
    )
    media_type: str = Field(
        ..., description="Type of substrate (e.g., 'wafer', 'tape', 'stick', 'grid')"
    )
    uid: Optional[str] = Field(
        None,
        description="Overall unique identifier for the substrate instance (e.g., from XML uid)",
    )
    status: Optional[str] = Field(
        "new",
        description="Status of the entire substrate (e.g., new, in_use, full, retired, damaged)",
    )
    refpoint: Optional[ReferencePoints] = Field(
        None, description="Reference points in local substrate coordinates"
    )
    refpoint_world: Optional[ReferencePoints] = Field(
        None, description="Reference points mapped to world/stage coordinates"
    )
    source_path: Optional[str] = Field(
        None,
        description="Path or identifier of the source file defining this substrate (e.g., XML path)",
    )
    metadata: Optional[SubstrateMetadata] = Field(
        None, description="General metadata about the substrate"
    )
    apertures: Optional[List[Aperture]] = Field(
        None,
        description="List of apertures or slots defined on this substrate, if applicable",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(None)

    class Settings:
        name = "substrates"

        indexes = [
            IndexModel(
                [("media_id", ASCENDING)], unique=True, name="media_id_unique_index"
            ),
            IndexModel([("media_type", ASCENDING)], name="media_type_index"),
            IndexModel(
                [("uid", ASCENDING)],
                unique=True,
                sparse=True,
                name="substrate_uid_index",
            ),
            IndexModel([("status", ASCENDING)], name="substrate_status_index"),
            IndexModel(
                [("apertures.uid", ASCENDING)], sparse=True, name="aperture_uid_index"
            ),
            IndexModel(
                [("apertures.status", ASCENDING)],
                sparse=True,
                name="aperture_status_index",
            ),
            IndexModel([("created_at", DESCENDING)], name="created_at_index"),
            IndexModel([("updated_at", DESCENDING)], name="updated_at_index"),
        ]


if __name__ == "__main__":
    import re
    from typing import Tuple
    from typing import Optional
    from typing import Dict
    from typing import Any
    from xml.etree import ElementTree as ET

    def parse_coord_string(
        coord_str: Optional[str],
    ) -> Optional[Tuple[float, float, float]]:
        if not coord_str:
            return None
        match = re.search(
            r"\(\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\)",
            coord_str,
        )
        if match:
            try:
                x = float(match.group(1))
                y = float(match.group(2))
                z = float(match.group(3))
                return (x, y, z)
            except (ValueError, IndexError):
                return None
        return None

    def parse_refpoint_dict_string(
        refpoint_str: Optional[str],
    ) -> Optional[ReferencePoints]:
        if not refpoint_str:
            return None
        try:
            points = {}
            origin_match = re.search(
                r"'origin':\s*\(\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\)",
                refpoint_str,
            )
            end_match = re.search(
                r"'end':\s*\(\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\)",
                refpoint_str,
            )
            ref_match = re.search(
                r"'ref':\s*\(\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\)",
                refpoint_str,
            )

            if origin_match:
                points["origin"] = (
                    float(origin_match.group(1)),
                    float(origin_match.group(2)),
                    float(origin_match.group(3)),
                )
            if end_match:
                points["end"] = (
                    float(end_match.group(1)),
                    float(end_match.group(2)),
                    float(end_match.group(3)),
                )
            if ref_match:
                points["ref"] = (
                    float(ref_match.group(1)),
                    float(ref_match.group(2)),
                    float(ref_match.group(3)),
                )

            return ReferencePoints(**points) if points else None

        except Exception:
            return None

    xml_data = """
    <?xml version='1.0' encoding='utf-8'?>
    <wafer media_id="0004" uid="2025042110054308" status="used" refpoint="{'origin': (30, -10.4, 0), 'end': (78.0, 72.7, 0), 'ref': (30.0, 72.7, 0)}" refpoint_world="{'origin': (30, -10.4, 10), 'end': (78.0, 72.7, 10), 'ref': (30.0, 72.7, 10)}" path="pylasso\navigator\lasso_wafer.xml">
        <metadata>
            <item key="Name">Wafer for SEM mesh</item>
            <item key="User">Lasso</item>
            <item key="created">2025-04-21 10:02:00</item>
            <item key="calibrated">2025-04-21 10:09:56</item>
        </metadata>
        <aperture uid="00040000" index="0" centroid="(24.0, 0.0, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="used" tuid="2025042110100136" />
        <aperture uid="00040001" index="1" centroid="(36.0, 0.0, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040002" index="2" centroid="(48.0, 0.0, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040003" index="3" centroid="(60.0, 0.0, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040004" index="4" centroid="(72.0, 0.0, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040005" index="5" centroid="(84.0, 0.0, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040006" index="6" centroid="(18.0, 10.392304845413264, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040007" index="7" centroid="(30.0, 10.392304845413264, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040008" index="8" centroid="(42.0, 10.392304845413264, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040009" index="9" centroid="(54.0, 10.392304845413264, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040010" index="10" centroid="(66.0, 10.392304845413264, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040011" index="11" centroid="(78.0, 10.392304845413264, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040012" index="12" centroid="(90.0, 10.392304845413264, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040013" index="13" centroid="(12.0, 20.784609690826528, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040014" index="14" centroid="(24.0, 20.784609690826528, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040015" index="15" centroid="(36.0, 20.784609690826528, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040016" index="16" centroid="(48.0, 20.784609690826528, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040017" index="17" centroid="(60.0, 20.784609690826528, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040018" index="18" centroid="(72.0, 20.784609690826528, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040019" index="19" centroid="(84.0, 20.784609690826528, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040020" index="20" centroid="(96.0, 20.784609690826528, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040021" index="21" centroid="(6.0, 31.17691453623979, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040022" index="22" centroid="(18.0, 31.17691453623979, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040023" index="23" centroid="(30.0, 31.17691453623979, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040024" index="24" centroid="(42.0, 31.17691453623979, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040025" index="25" centroid="(54.0, 31.17691453623979, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040026" index="26" centroid="(66.0, 31.17691453623979, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040027" index="27" centroid="(78.0, 31.17691453623979, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040028" index="28" centroid="(90.0, 31.17691453623979, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040029" index="29" centroid="(102.0, 31.17691453623979, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040030" index="30" centroid="(12.0, 41.569219381653056, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040031" index="31" centroid="(24.0, 41.569219381653056, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040032" index="32" centroid="(36.0, 41.569219381653056, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040033" index="33" centroid="(48.0, 41.569219381653056, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040034" index="34" centroid="(60.0, 41.569219381653056, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040035" index="35" centroid="(72.0, 41.569219381653056, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040036" index="36" centroid="(84.0, 41.569219381653056, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040037" index="37" centroid="(96.0, 41.569219381653056, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040038" index="38" centroid="(18.0, 51.96152422706631, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040039" index="39" centroid="(30.0, 51.96152422706631, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040040" index="40" centroid="(42.0, 51.96152422706631, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040041" index="41" centroid="(54.0, 51.96152422706631, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040042" index="42" centroid="(66.0, 51.96152422706631, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040043" index="43" centroid="(78.0, 51.96152422706631, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040044" index="44" centroid="(90.0, 51.96152422706631, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040045" index="45" centroid="(24.0, 62.35382907247958, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040046" index="46" centroid="(36.0, 62.35382907247958, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040047" index="47" centroid="(48.0, 62.35382907247958, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040048" index="48" centroid="(60.0, 62.35382907247958, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040049" index="49" centroid="(72.0, 62.35382907247958, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040050" index="50" centroid="(84.0, 62.35382907247958, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040051" index="51" centroid="(42.0, 72.74613391789285, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040052" index="52" centroid="(54.0, 72.74613391789285, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
        <aperture uid="00040053" index="53" centroid="(66.0, 72.74613391789285, -0.0)" shape="Circle:{&quot;diameter&quot;: 10.2}" status="available" tuid="0" />
    </wafer>
    """.strip()
    root = ET.fromstring(xml_data)

    media_id = root.attrib.get("media_id")
    wafer_uid = root.attrib.get("uid")
    wafer_status = root.attrib.get("status")
    wafer_path = root.attrib.get("path")
    refpoint_str = root.attrib.get("refpoint")
    refpoint_world_str = root.attrib.get("refpoint_world")

    refpoint_data = parse_refpoint_dict_string(refpoint_str)
    refpoint_world_data = parse_refpoint_dict_string(refpoint_world_str)

    metadata_items = {}
    metadata_node = root.find("metadata")
    if metadata_node is not None:
        for item in metadata_node.findall("item"):
            key = item.attrib.get("key")
            value = item.text
            if key:
                metadata_items[key.lower()] = value

    substrate_meta = SubstrateMetadata(
        name=metadata_items.get("name"),
        user=metadata_items.get("user"),
        created=(
            datetime.fromisoformat(metadata_items["created"])
            if "created" in metadata_items
            else None
        ),
        calibrated=(
            datetime.fromisoformat(metadata_items["calibrated"])
            if "calibrated" in metadata_items
            else None
        ),
        other={
            k: v
            for k, v in metadata_items.items()
            if k not in ["name", "user", "created", "calibrated"]
        },
    )

    apertures_list = []
    for aperture_node in root.findall("aperture"):
        try:
            aperture_data = Aperture(
                uid=aperture_node.attrib.get("uid"),
                index=int(aperture_node.attrib.get("index", -1)),
                centroid=parse_coord_string(aperture_node.attrib.get("centroid")),
                shape=aperture_node.attrib.get("shape"),
                status=aperture_node.attrib.get("status"),
                tracking_uid=aperture_node.attrib.get("tuid"),
            )
            apertures_list.append(aperture_data)
        except (ValueError, TypeError, KeyError) as e:
            print(
                f"Warning: Skipping aperture due to parsing error: {e}. Node: {ET.tostring(aperture_node)}"
            )
            continue

    if media_id:
        substrate_doc_data = {
            "media_id": media_id,
            "media_type": "wafer",
            "uid": wafer_uid,
            "status": wafer_status,
            "source_path": wafer_path,
            "refpoint": refpoint_data,
            "refpoint_world": refpoint_world_data,
            "metadata": substrate_meta,
            "apertures": apertures_list if apertures_list else None,
        }

        substrate_doc = SubstrateCreate(**substrate_doc_data)

        print("Successfully created Substrate document instance:")
        print(substrate_doc.model_dump_json(indent=2))

    else:
        print(
            "Error: Could not create Substrate document, missing mandatory media_id in XML."
        )
