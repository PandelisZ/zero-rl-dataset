"""Thin wrapper around the native `zero` toolchain.

Every reward in this dataset is grounded in real `zero` invocations (no
simulated compilers). This module materializes a submission into a temporary
workspace and shells out to `zero check` / `zero run` / `zero test`.

Verified against `zero 0.2.0`.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass


_INSTALL_ATTEMPTED = False


def zero_bin() -> str:
    """Locate the `zero` binary (PATH, then ~/.zero/bin), auto-installing once.

    Prime's hosted env-servers are clean containers without `zero`, so on first
    use we lazily install the toolchain via the official installer. Set
    ZERO_NO_AUTOINSTALL=1 to disable.
    """
    found = shutil.which("zero")
    if found:
        return found
    default = os.path.expanduser("~/.zero/bin/zero")
    if os.path.exists(default):
        return default

    global _INSTALL_ATTEMPTED
    if not _INSTALL_ATTEMPTED and os.environ.get("ZERO_NO_AUTOINSTALL") != "1":
        _INSTALL_ATTEMPTED = True
        try:
            subprocess.run(
                "curl -fsSL https://zerolang.ai/install.sh | bash",
                shell=True, capture_output=True, text=True, timeout=300,
            )
        except Exception:
            pass
        if os.path.exists(default):
            return default

    raise FileNotFoundError(
        "`zero` not found on PATH or ~/.zero/bin and auto-install failed. "
        "Install with: curl -fsSL https://zerolang.ai/install.sh | bash"
    )


def zero_version() -> str:
    try:
        out = subprocess.run([zero_bin(), "--version"], capture_output=True, text=True, timeout=30)
        return out.stdout.strip() or out.stderr.strip()
    except Exception as exc:  # pragma: no cover - diagnostic only
        return f"unknown ({exc})"


@dataclass
class ProcResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


def _run(args: list[str], cwd: str, timeout_sec: int) -> ProcResult:
    try:
        proc = subprocess.run(
            [zero_bin(), *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        return ProcResult(proc.returncode == 0, proc.returncode, proc.stdout, proc.stderr)
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return ProcResult(False, -1, out, err, timed_out=True)


def materialize(files: dict[str, str]) -> str:
    """Write {relpath: content} into a fresh temp workspace; return its path."""
    workspace = tempfile.mkdtemp(prefix="zero_ws_")
    for relpath, content in files.items():
        dest = os.path.join(workspace, relpath)
        os.makedirs(os.path.dirname(dest) or workspace, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(content)
    return workspace


def is_project(files: dict[str, str]) -> bool:
    return any(os.path.basename(p) == "zero.json" for p in files)


def check(workspace: str, target: str, timeout_sec: int) -> ProcResult:
    return _run(["check", target], workspace, timeout_sec)


def run(workspace: str, target: str, timeout_sec: int, args: list[str] | None = None) -> ProcResult:
    cmd = ["run", target]
    if args:
        cmd += ["--", *args]
    return _run(cmd, workspace, timeout_sec)


def test(workspace: str, target: str, timeout_sec: int) -> ProcResult:
    return _run(["test", target], workspace, timeout_sec)


def parse_test_counts(stdout: str, stderr: str) -> tuple[int, int]:
    """Return (passed, total). `zero test` prints 'N test(s) ok' on success."""
    blob = f"{stdout}\n{stderr}"
    import re

    m = re.search(r"(\d+)\s+test\(s\) ok", blob)
    if m:
        n = int(m.group(1))
        return n, n
    return 0, 0
