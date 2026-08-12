from typing import get_args

from temdb.models import RUN_STATUSES, AcquisitionStatusFilter, SectionQuality


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


class TestAcquisitionStatusFilter:
    def test_covers_run_statuses_plus_in_flight(self):
        assert get_args(AcquisitionStatusFilter) == RUN_STATUSES + ("in_flight",)
