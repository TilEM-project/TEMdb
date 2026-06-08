from temdb.models import AcquisitionStatus, SectionQuality


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


class TestAcquisitionStatus:
    def test_all_values_exist(self):
        assert AcquisitionStatus.ABORTED == "aborted"
        assert AcquisitionStatus.QC_FAILED == "failed"
        assert AcquisitionStatus.QC_PASSED == "qc-passed"
        assert AcquisitionStatus.QC_PENDING == "qc-pending"

    def test_is_string_enum(self):
        assert isinstance(AcquisitionStatus.QC_PENDING, str)

    def test_all_members_count(self):
        assert len(AcquisitionStatus) == 4
