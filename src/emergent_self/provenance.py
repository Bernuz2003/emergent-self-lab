"""What produced a result.

A config digest says which *settings* a run used. It says nothing about which
*code* ran, so two runs with the same digest and materially different physics
are indistinguishable after the fact. Every result file therefore records the
git commit, whether the working tree was dirty at the time, the package version
and the interpreter version.

`dirty` is the field that matters most in practice: a commit hash recorded while
uncommitted edits were present does not identify the code that ran, and a result
carrying `dirty: true` should not be treated as reproducible.
"""
from __future__ import annotations

import functools
import platform
import subprocess
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(_REPO), *args],
            capture_output=True, text=True, timeout=5, check=False,
        )
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


@functools.lru_cache(maxsize=1)
def provenance() -> dict[str, Any]:
    """Collected once per process; git calls are not free and never change."""
    try:
        from importlib.metadata import PackageNotFoundError, version

        try:
            pkg = version("emergent-self-lab")
        except PackageNotFoundError:
            pkg = None
    except ImportError:
        pkg = None

    commit = _git("rev-parse", "HEAD")
    status = _git("status", "--porcelain")
    return {
        "git_commit": commit,
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        # None when this is not a git checkout at all, which is itself worth
        # recording: such a result cannot be traced to any revision.
        "dirty_worktree": None if status is None else bool(status),
        "package_version": pkg,
        "python_version": platform.python_version(),
        "numpy_version": _numpy_version(),
        "platform": platform.platform(),
    }


def _numpy_version() -> str | None:
    try:
        import numpy

        return numpy.__version__
    except ImportError:
        return None


def describe() -> str:
    """One line for a console header."""
    p = provenance()
    if p["git_commit"] is None:
        return f"code: not a git checkout | py {p['python_version']} | numpy {p['numpy_version']}"
    flag = " +DIRTY" if p["dirty_worktree"] else ""
    return (f"code: {p['git_commit'][:10]}{flag} ({p['git_branch']}) | "
            f"py {p['python_version']} | numpy {p['numpy_version']}")


def warn_if_dirty() -> None:
    p = provenance()
    if p["dirty_worktree"]:
        print("warning: the working tree has uncommitted changes, so the recorded "
              "commit does not identify the code that produced this result.")
    elif p["git_commit"] is None:
        print("warning: not a git checkout; this result cannot be traced to a revision.")
