import argparse
import importlib.metadata
import json
import logging
import os
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config

from temdb.server.contract_diff import compare, rank, required_bump
from temdb.server.main import create_app


def alembic_ini_path() -> Path:
    """Locate alembic.ini in the installed package or the source checkout."""
    package_root = Path(__file__).resolve().parent.parent
    for candidate in (package_root / "alembic.ini", package_root.parent.parent / "alembic.ini"):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"alembic.ini not found next to {package_root} or in the source layout. "
        "If this is an installed package the wheel was built without its migrations."
    )


def run_migrations(revision: str = "head", url: str | None = None) -> None:
    """Upgrade the database to `revision`; `url` sets TEMDB_MIGRATION_URL for this process."""
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


def openapi_main() -> None:
    """Print the OpenAPI spec as JSON to stdout, for client generators."""
    logging.disable(logging.CRITICAL)
    print(json.dumps(create_app().openapi(), indent=2, sort_keys=True))


def contract_check_main(argv: list[str] | None = None) -> None:
    """Report the version bump the API changes need versus the released contract.

    Exits 1 if --bump is lower than required. --record saves the current API as the released contract.
    """
    logging.disable(logging.CRITICAL)
    parser = argparse.ArgumentParser(prog="temdb-contract-check", description=contract_check_main.__doc__)
    parser.add_argument("--baseline", default="contract/openapi.released.json", help="the released contract")
    parser.add_argument("--bump", choices=["patch", "minor", "major"], help="the bump about to be released")
    parser.add_argument("--record", action="store_true", help="store the current API as the released contract")
    args = parser.parse_args(argv)
    current = json.loads(json.dumps(create_app().openapi()))
    if args.record:
        released = {"version": importlib.metadata.version("temdb-models"), "spec": current}
        Path(args.baseline).write_text(json.dumps(released, indent=2, sort_keys=True) + "\n")
        print(f"Recorded the API as the released contract for {released['version']}")
        return
    released = json.loads(Path(args.baseline).read_text())
    changes = compare(released["spec"], current)
    for change in changes:
        print(f"{change.bump:5}  {change.where}: {change.what}")
    needed = required_bump(changes)
    print(f"Since {released['version']} the API needs a {needed} bump ({len(changes)} changes).")
    if args.bump is not None and rank(args.bump) < rank(needed):
        print(f"A {args.bump} release would break clients that check the models version; release {needed}.")
        raise SystemExit(1)
