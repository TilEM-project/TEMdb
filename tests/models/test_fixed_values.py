import re
from enum import Enum

import httpx
import pytest
from pydantic import ValidationError

from temdb.models import (
    QC_STATES,
    RUN_STATUSES,
    SECTION_CONDITIONS,
    TASK_KINDS,
    TRANSFER_STATES,
    AcquisitionCreate,
    AcquisitionResponse,
    AcquisitionStatus,
    AcquisitionTaskCreate,
    AcquisitionTaskResponse,
    AcquisitionTaskUpdate,
    AcquisitionUpdate,
    QCState,
    SectionCondition,
    SectionResponse,
    SectionUpdate,
    TaskKind,
    TransferState,
    enums,
)
from temdb.server.api.v2.quality_control import HeatmapType
from temdb.server.sqlmodels import AcquisitionSQLModel

FIELDS = [
    (SectionCondition, SectionUpdate, "condition"),
    (TaskKind, AcquisitionTaskUpdate, "kind"),
    (AcquisitionStatus, AcquisitionUpdate, "status"),
    (QCState, AcquisitionUpdate, "qc_state"),
    (TransferState, AcquisitionUpdate, "transfer_state"),
]


@pytest.mark.parametrize(("enum", "model", "field"), FIELDS)
def test_every_value_is_accepted_as_text_and_sent_as_text(enum, model, field):
    for member in enum:
        built = model(**{field: member.value})

        assert getattr(built, field) is member
        assert getattr(built, field) == member.value
        assert built.model_dump(mode="json")[field] == member.value


@pytest.mark.parametrize(("enum", "model", "field"), FIELDS)
def test_any_other_value_is_refused(enum, model, field):
    with pytest.raises(ValidationError, match=field):
        model(**{field: "not-a-value"})


@pytest.mark.parametrize(
    ("model", "field", "enum"),
    [
        (AcquisitionCreate, "kind", TaskKind),
        (AcquisitionResponse, "kind", TaskKind),
        (AcquisitionResponse, "status", AcquisitionStatus),
        (AcquisitionResponse, "qc_state", QCState),
        (AcquisitionResponse, "transfer_state", TransferState),
        (AcquisitionTaskCreate, "kind", TaskKind),
        (AcquisitionTaskResponse, "kind", TaskKind),
        (SectionResponse, "condition", SectionCondition),
    ],
)
def test_every_model_with_the_field_uses_the_enum(model, field, enum):
    assert enum in (
        model.model_fields[field].annotation,
        *getattr(model.model_fields[field].annotation, "__args__", ()),
    )


@pytest.mark.parametrize(
    ("constraint", "enum"),
    [
        ("kind_vocab", TaskKind),
        ("status_vocab", AcquisitionStatus),
        ("qc_state_vocab", QCState),
        ("transfer_state_vocab", TransferState),
    ],
)
def test_database_constraints_allow_exactly_the_enum_values(constraint, enum):
    check = next(c for c in AcquisitionSQLModel.__table__.constraints if c.name == f"ck_acquisitions_{constraint}")

    assert set(re.findall(r"'([^']+)'", str(check.sqltext))) == {member.value for member in enum}


@pytest.mark.parametrize(
    ("values", "enum"),
    [
        (SECTION_CONDITIONS, SectionCondition),
        (TASK_KINDS, TaskKind),
        (RUN_STATUSES, AcquisitionStatus),
        (QC_STATES, QCState),
        (TRANSFER_STATES, TransferState),
    ],
)
def test_the_old_value_lists_follow_the_enums(values, enum):
    assert values == tuple(member.value for member in enum)


@pytest.mark.parametrize("field", ["status", "qc_state", "transfer_state"])
def test_an_update_cannot_set_a_state_to_null(field):
    """status is write-once; qc_state and transfer_state are NOT NULL columns."""
    with pytest.raises(ValidationError, match=field):
        AcquisitionUpdate(**{field: None})


ENUMS = [value for value in vars(enums).values() if isinstance(value, type) and issubclass(value, Enum)] + [HeatmapType]


@pytest.mark.parametrize("member", [member for enum in ENUMS if enum is not Enum for member in enum], ids=repr)
def test_a_value_reads_as_its_text_in_strings_and_query_parameters(member):
    assert str(member) == member.value
    assert f"{member}" == member.value
    assert httpx.Request("GET", "http://test/", params={"value": member}).url.params["value"] == member.value


RESPONSE_FIELDS = [
    (AcquisitionResponse, "kind", TaskKind),
    (AcquisitionResponse, "status", AcquisitionStatus),
    (AcquisitionResponse, "qc_state", QCState),
    (AcquisitionResponse, "transfer_state", TransferState),
    (AcquisitionTaskResponse, "kind", TaskKind),
    (SectionResponse, "condition", SectionCondition),
]


def validated(model, field, value):
    instance = model.model_construct()
    model.__pydantic_validator__.validate_assignment(instance, field, value)
    return getattr(instance, field)


@pytest.mark.parametrize(("model", "field", "enum"), RESPONSE_FIELDS)
def test_a_response_refuses_a_value_this_version_does_not_know(model, field, enum):
    """Adding a value to one of these enums is a major version change."""
    with pytest.raises(ValidationError, match=field):
        validated(model, field, "added_later")
