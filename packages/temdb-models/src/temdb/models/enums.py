from enum import StrEnum
from typing import Literal


class SectionQuality(StrEnum):
    GOOD = "good"
    BROKEN = "broken"
    THIN = "thin"
    THICK = "thick"
    EMPTY = "empty"


class MatchPosition(StrEnum):
    INVALID = "invalid"
    CENTER = "center"
    LEFT = "left"
    TOP = "top"
    RIGHT = "right"
    BOTTOM = "bottom"


class SectionImage(StrEnum):
    POST_PICKUP = "post_pickup_image"
    POST_DROPOFF = "post_dropoff_image"
    QC = "qc_image"


class StorageProtocol(StrEnum):
    S3 = "s3"
    GCS = "gcs"


class SubstrateType(StrEnum):
    GRID_DISC = "grid_disc"
    WAFER = "wafer"
    TAPE = "tape"
    STICK = "stick"
    GRID = "grid"
    WASHER = "washer"
    UNKNOWN = "unknown"


class ApertureStatus(StrEnum):
    AVAILABLE = "available"
    USED = "used"
    DAMAGED = "damaged"


class ShapeType(StrEnum):
    CIRCLE = "circle"
    SLOT = "slot"
    RECTANGLE = "rectangle"
    TRIANGLE = "triangle"
    CIRCLE_ARRAY = "circle_array"
    POLYGON = "polygon"


class AcquisitionStatus(StrEnum):
    COMPLETE = "complete"
    ABORTED = "aborted"
    FAILED = "failed"


class QCState(StrEnum):
    PENDING = "pending"
    QC_PASS = "qc_pass"
    QC_FAIL = "qc_fail"
    NEEDS_REVIEW = "needs_review"


class TransferState(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    ERROR = "error"


class SectionCondition(StrEnum):
    OK = "ok"
    DAMAGED = "damaged"
    DESTROYED = "destroyed"
    CONTAMINATED = "contaminated"
    LOST = "lost"


class TaskKind(StrEnum):
    MONTAGE = "montage"
    LENS_CORRECTION = "lens_correction"


RUN_STATUSES = tuple(status.value for status in AcquisitionStatus)
AcquisitionStatusFilter = Literal["complete", "aborted", "failed", "in_flight"]
QC_STATES = tuple(state.value for state in QCState)
TRANSFER_STATES = tuple(state.value for state in TransferState)
SECTION_CONDITIONS = tuple(condition.value for condition in SectionCondition)
TASK_KINDS = tuple(kind.value for kind in TaskKind)
