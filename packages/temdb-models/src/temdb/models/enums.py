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


class SectionImage(str, Enum):
    POST_PICKUP = "post_pickup_image"
    POST_DROPOFF = "post_dropoff_image"
    QC = "qc_image"


class StorageProtocol(str, Enum):
    S3 = "s3"
    GCS = "gcs"


class SubstrateType(str, Enum):
    GRID_DISC = "grid_disc"
    WAFER = "wafer"
    TAPE = "tape"
    STICK = "stick"
    GRID = "grid"
    WASHER = "washer"
    UNKNOWN = "unknown"


class ApertureStatus(str, Enum):
    AVAILABLE = "available"
    USED = "used"
    DAMAGED = "damaged"


class ShapeType(str, Enum):
    CIRCLE = "circle"
    SLOT = "slot"
    RECTANGLE = "rectangle"
    TRIANGLE = "triangle"
    CIRCLE_ARRAY = "circle_array"
    POLYGON = "polygon"


class AcquisitionStatus(str, Enum):
    COMPLETE = "complete"
    ABORTED = "aborted"
    FAILED = "failed"


class QCState(str, Enum):
    PENDING = "pending"
    QC_PASS = "qc_pass"
    QC_FAIL = "qc_fail"
    NEEDS_REVIEW = "needs_review"


class TransferState(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    ERROR = "error"


class SectionCondition(str, Enum):
    OK = "ok"
    DAMAGED = "damaged"
    DESTROYED = "destroyed"
    CONTAMINATED = "contaminated"
    LOST = "lost"


class TaskKind(str, Enum):
    MONTAGE = "montage"
    LENS_CORRECTION = "lens_correction"


RUN_STATUSES = tuple(status.value for status in AcquisitionStatus)
AcquisitionStatusFilter = Literal["complete", "aborted", "failed", "in_flight"]
QC_STATES = tuple(state.value for state in QCState)
TRANSFER_STATES = tuple(state.value for state in TransferState)
SECTION_CONDITIONS = tuple(condition.value for condition in SectionCondition)
TASK_KINDS = tuple(kind.value for kind in TaskKind)
