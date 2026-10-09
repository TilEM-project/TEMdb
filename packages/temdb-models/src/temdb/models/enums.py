from enum import Enum
from typing import Literal


class SectionQuality(str, Enum):
    GOOD = "good"
    BROKEN = "broken"
    THIN = "thin"
    THICK = "thick"
    EMPTY = "empty"


class MatchPosition(str, Enum):
    INVALID = "invalid"
    CENTER = "center"
    LEFT = "left"
    TOP = "top"
    RIGHT = "right"
    BOTTOM = "bottom"


class SubstrateType(str, Enum):
    GRID_DISC = "grid_disc"
    WAFER = "wafer"
    TAPE = "tape"
    STICK = "stick"
    GRID = "grid"
    WASHER = "washer"


class ApertureCondition(str, Enum):
    OK = "ok"
    DAMAGED = "damaged"
    MISSING = "missing"
    BURST = "burst"
    CONTAMINATED = "contaminated"


class ShapeType(str, Enum):
    CIRCLE = "circle"
    SLOT = "slot"
    RECTANGLE = "rectangle"
    TRIANGLE = "triangle"
    CIRCLE_ARRAY = "circle_array"


RUN_STATUSES = ("complete", "aborted", "failed")
AcquisitionStatusFilter = Literal["complete", "aborted", "failed", "in_flight"]
QC_STATES = ("pending", "qc_pass", "qc_fail", "needs_review")
TRANSFER_STATES = ("not_started", "in_progress", "complete", "error")
SECTION_CONDITIONS = ("ok", "damaged", "destroyed", "contaminated", "lost")
TASK_KINDS = ("montage", "lens_correction")
