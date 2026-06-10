from enum import Enum


class SectionQuality(str, Enum):
    GOOD = "good"
    BROKEN = "broken"
    THIN = "thin"
    THICK = "thick"
    EMPTY = "empty"


class AcquisitionStatus(str, Enum):
    ABORTED = "aborted"
    QC_FAILED = "failed"
    QC_PASSED = "qc-passed"
    QC_PENDING = "qc-pending"


class AcquisitionTaskStatus(str, Enum):
    PLANNED = "Planned"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    FAILED = "Failed"
    ABORTED = "Aborted"


class MatchPosition(str, Enum):
    INVALID = "invalid"
    CENTER = "center"
    LEFT = "left"
    TOP = "top"
    RIGHT = "right"
    BOTTOM = "bottom"


RUN_STATUSES = ("complete", "aborted", "failed")
QC_STATES = ("pending", "qc_pass", "qc_fail", "needs_review")
TRANSFER_STATES = ("not_started", "in_progress", "complete", "error")
SECTION_CONDITIONS = ("ok", "damaged", "destroyed", "contaminated", "lost")
TASK_KINDS = ("montage", "lens_correction")
