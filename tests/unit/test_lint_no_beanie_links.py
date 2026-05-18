import textwrap
from pathlib import Path

from tools.lint_no_beanie_links import scan_paths


def test_flags_link_import(tmp_path: Path):
    bad = tmp_path / "bad.py"
    bad.write_text(textwrap.dedent("""
        from beanie import Document, Link
        class X(Document):
            pass
    """))
    violations = scan_paths([tmp_path])
    assert len(violations) == 1
    assert "Link" in violations[0].message


def test_flags_backlink_import(tmp_path: Path):
    bad = tmp_path / "bad.py"
    bad.write_text(textwrap.dedent("""
        from beanie.odm.fields import BackLink
    """))
    violations = scan_paths([tmp_path])
    assert len(violations) == 1
    assert "BackLink" in violations[0].message


def test_allows_pydantic_object_id(tmp_path: Path):
    good = tmp_path / "good.py"
    good.write_text(textwrap.dedent("""
        from beanie import Document
        from beanie.odm.fields import PydanticObjectId
    """))
    assert scan_paths([tmp_path]) == []


def test_temdb_server_is_clean():
    """Production guard: the actual server tree must have no banned imports."""
    server_root = Path(__file__).resolve().parents[2] / "packages/temdb/src/temdb/server"
    assert server_root.exists(), f"server root missing: {server_root}"
    assert scan_paths([server_root]) == []
