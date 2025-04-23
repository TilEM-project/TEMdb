from enum import Enum


class SectionQuality(str, Enum):
    GOOD = "good"
    BROKEN = "broken"
    THIN = "thin"
    THICK = "thick"
    EMPTY = "empty"


class AcquisitionTaskStatus(str, Enum):
    PLANNED = "Planned"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    FAILED = "Failed"
    ABORTED = "Aborted"


class AcquisitionStatus(str, Enum):
    IMAGING = "imaging"
    ACQUIRED = "acquired"
    ABORTED = "aborted"
    QC_FAILED = "failed"
    QC_PASSED = "qc-passed"
    TO_BE_REIMAGED = "to be re-imaged"
