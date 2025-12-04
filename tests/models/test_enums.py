from temdb.models import AcquisitionStatus, AcquisitionTaskStatus, SectionQuality


class TestSectionQuality:
    def test_all_values_exist(self):
        assert SectionQuality.GOOD == "good"
        assert SectionQuality.BROKEN == "broken"
        assert SectionQuality.THIN == "thin"
        assert SectionQuality.THICK == "thick"
        assert SectionQuality.EMPTY == "empty"

    def test_is_string_enum(self):
        assert isinstance(SectionQuality.GOOD, str)
        assert SectionQuality.GOOD.value == "good"

    def test_all_members_count(self):
        assert len(SectionQuality) == 5


class TestAcquisitionTaskStatus:
    def test_all_values_exist(self):
        assert AcquisitionTaskStatus.PLANNED == "Planned"
        assert AcquisitionTaskStatus.IN_PROGRESS == "In Progress"
        assert AcquisitionTaskStatus.COMPLETED == "Completed"
        assert AcquisitionTaskStatus.FAILED == "Failed"
        assert AcquisitionTaskStatus.ABORTED == "Aborted"

    def test_is_string_enum(self):
        assert isinstance(AcquisitionTaskStatus.PLANNED, str)

    def test_all_members_count(self):
        assert len(AcquisitionTaskStatus) == 5


class TestAcquisitionStatus:
    def test_all_values_exist(self):
        assert AcquisitionStatus.IMAGING == "imaging"
        assert AcquisitionStatus.ACQUIRED == "acquired"
        assert AcquisitionStatus.ABORTED == "aborted"
        assert AcquisitionStatus.QC_FAILED == "failed"
        assert AcquisitionStatus.QC_PASSED == "qc-passed"
        assert AcquisitionStatus.QC_PENDING == "qc-pending"
        assert AcquisitionStatus.TO_BE_REIMAGED == "to be re-imaged"

    def test_is_string_enum(self):
        assert isinstance(AcquisitionStatus.IMAGING, str)

    def test_all_members_count(self):
        assert len(AcquisitionStatus) == 7
