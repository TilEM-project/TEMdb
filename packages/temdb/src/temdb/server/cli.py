import argparse
import os
from pathlib import Path


def alembic_ini_path() -> Path:
    package_root = Path(__file__).resolve().parent.parent
    for candidate in (package_root / "alembic.ini", package_root.parent.parent / "alembic.ini"):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"alembic.ini not found next to {package_root} or in the source layout. "
        "If this is an installed package the wheel was built without its migrations."
    )


def run_migrations(revision: str = "head", url: str | None = None) -> None:
    from alembic import command
    from alembic.config import Config

    if url:
        os.environ["TEMDB_MIGRATION_URL"] = url
    command.upgrade(Config(str(alembic_ini_path())), revision)


def migrate_main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="temdb-migrate", description="Apply TEMdb database migrations.")
    parser.add_argument("--revision", default="head", help="target revision (default: head)")
    parser.add_argument("--url", default=None, help="database URL; overrides TEMDB_MIGRATION_URL")
    args = parser.parse_args(argv)
    run_migrations(args.revision, args.url)


def server_main(argv: list[str] | None = None) -> None:
    import uvicorn

    parser = argparse.ArgumentParser(prog="temdb-server", description="Run the TEMdb API server.")
    parser.add_argument("--host", default=os.getenv("TEMDB_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("TEMDB_PORT", "8000")))
    parser.add_argument("--log-level", default=os.getenv("TEMDB_LOG_LEVEL", "info"))
    args = parser.parse_args(argv)
    uvicorn.run(
        "temdb.server.main:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )
