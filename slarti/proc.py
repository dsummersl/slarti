from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


class ToolMissing(Exception):
    """Raised when a delegated tool binary cannot be found."""


@dataclass(frozen=True)
class Result:
    """The outcome of a delegated subprocess."""

    code: int
    stdout: str
    stderr: str


def run(argv: list[str], cwd: Path | None = None) -> Result:
    """Run a delegated tool and capture its output verbatim."""
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ToolMissing(argv[0]) from exc
    return Result(code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)


def passthrough(result: Result) -> None:
    """Emit a delegated tool's diagnostics unaltered (I2)."""
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)


def likec4(args: list[str]) -> list[str]:
    """Argv for the user's pinned LikeC4, never installing anything."""
    return ["npx", "--no-install", "likec4", *args]
