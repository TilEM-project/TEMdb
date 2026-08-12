import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from temdb.server.sqlmodels import LensCorrectionSQLModel, MicroscopeSQLModel


async def test_lens_correction_roundtrip(session):
    scope = MicroscopeSQLModel(label="TEM-01")
    session.add(scope)
    await session.flush()
    assert scope.microscope_id is not None
    lc = LensCorrectionSQLModel(
        microscope_id=scope.microscope_id, magnification=20000,
        started_at=datetime.now(timezone.utc),
        correction_x_uri="s3://bucket/lc/x.tiff", correction_y_uri="s3://bucket/lc/y.tiff",
    )
    session.add(lc)
    await session.flush()
    assert lc.lc_id is not None


async def test_lens_correction_requires_microscope(session):
    lc = LensCorrectionSQLModel(
        microscope_id=uuid.uuid4(), magnification=20000,
        started_at=datetime.now(timezone.utc),
    )
    session.add(lc)
    with pytest.raises(IntegrityError):
        await session.flush()
