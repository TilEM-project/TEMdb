"""Fail if `Link` or `BackLink` is imported anywhere under the given paths.

Usage:
    uv run python -m tools.lint_no_beanie_links packages/temdb/src/temdb/server/
"""
import ast
import sys
from dataclasses import dataclass
from pathlib import Path

BANNED = {"Link", "BackLink"}


@dataclass
class Violation:
    path: Path
    lineno: int
    message: str


def scan_paths(paths: list[Path]) -> list[Violation]:
    out: list[Violation] = []
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(p.rglob("*.py"))
        elif p.suffix == ".py":
            files.append(p)

    for f in files:
        tree = ast.parse(f.read_text(), filename=str(f))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and "beanie" in node.module:
                for alias in node.names:
                    if alias.name in BANNED:
                        out.append(
                            Violation(
                                path=f,
                                lineno=node.lineno,
                                message=f"Forbidden import `{alias.name}` from {node.module}",
                            )
                        )
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: lint_no_beanie_links.py <path> [...]", file=sys.stderr)
        return 2
    violations = scan_paths([Path(a) for a in sys.argv[1:]])
    for v in violations:
        print(f"{v.path}:{v.lineno}: {v.message}", file=sys.stderr)
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
