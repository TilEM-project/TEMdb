from enum import Enum


class MediaType(str, Enum):
    TAPE = "tape"
    GRID = "grid"
    SLED = "sled"
    STICK = "stick"


class SectionQuality(str, Enum):
    GOOD = "good"
    BROKEN = "broken"
    THIN = "thin"
    THICK = "thick"
    EMPTY = "empty"


class ImagingSessionStatus(str, Enum):
    PLANNED = "Planned"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    FAILED = "Failed"


class AcquisitionStatus(str, Enum):
    ACQUIRED = "acquired"
    ABORTED = "aborted"
    QC_FAILED = "failed"
    QC_PASSED = "qc-passed"
    TO_BE_REIMAGED = "to be re-imaged"
