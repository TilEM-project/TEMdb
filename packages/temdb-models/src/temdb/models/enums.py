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


RUN_STATUSES = ("complete", "aborted", "failed")
AcquisitionStatusFilter = Literal["complete", "aborted", "failed", "in_flight"]
QC_STATES = ("pending", "qc_pass", "qc_fail", "needs_review")
TRANSFER_STATES = ("not_started", "in_progress", "complete", "error")
SECTION_CONDITIONS = ("ok", "damaged", "destroyed", "contaminated", "lost")
TASK_KINDS = ("montage", "lens_correction")
