"""Generate verified `zero_package_edit` tasks from the 10 real projects.

For each project in ../zerolang-examples/projects, one tested function in
lib.0 is replaced with a type-correct but wrong stub. This yields a "before"
state that still passes `zero check` but FAILS `zero test`. The model must
restore correct behaviour; the oracle is the original project.

Verified: before compiles + fails tests; after (original) compiles + passes.
"""
from __future__ import annotations

import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

ZERO_VERSION = common.zero_runner.zero_version()
EXAMPLES = os.path.abspath(os.path.join(common.ROOT, "..", "zerolang-examples", "projects"))

# project -> (function to stub, wrong but type-correct body return)
TARGETS = {
    "zgrep": ("byte_eq", "    return false\n"),
    "zwc": ("is_space", "    return false\n"),
    "zcalc": ("apply_op", "    return 0\n"),
    "zsort": ("cmp_u32", "    return 0\n"),
    "zcut": ("at_least_one", "    return 0_u32\n"),
    "ztr": ("rot13_byte", "    return 0_u8\n"),
    "zbase": ("pow_u32", "    return 0_u32\n"),
    "zfactor": ("is_prime", "    return false\n"),
    "zuniq": ("is_dup_count", "    return false\n"),
    "zstats": ("min2", "    return 0_u32\n"),
}


def stub_function(src: str, name: str, new_body: str) -> str | None:
    """Replace the body of `pub fn name(...) { ... }` with new_body."""
    anchor = src.find(f"pub fn {name}")
    if anchor == -1:
        return None
    open_brace = src.find("{", anchor)
    if open_brace == -1:
        return None
    depth = 0
    i = open_brace
    while i < len(src):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    if depth != 0:
        return None
    return src[: open_brace + 1] + "\n" + new_body + src[i:]


def read_project(name: str) -> dict:
    base = os.path.join(EXAMPLES, name)
    files = {}
    for rel in ("zero.json", "src/main.0", "src/lib.0"):
        p = os.path.join(base, rel)
        with open(p, encoding="utf-8") as fh:
            files[rel] = fh.read()
    return files


def project_passes(files: dict) -> tuple[bool, bool]:
    """Return (check_ok, test_ok) for a project file set."""
    ws = common.zero_runner.materialize(files)
    try:
        chk = common.zero_runner.check(ws, ".", 90)
        if not chk.ok:
            return False, False
        tst = common.zero_runner.test(ws, ".", 90)
        passed, _ = common.zero_runner.parse_test_counts(tst.stdout, tst.stderr)
        return True, (tst.ok and passed > 0)
    finally:
        shutil.rmtree(ws, ignore_errors=True)


def main():
    rows = []
    failures = []
    for name, (func, body) in TARGETS.items():
        original = read_project(name)
        ok_chk, ok_test = project_passes(original)
        if not (ok_chk and ok_test):
            failures.append((name, "original project does not pass check+test"))
            continue

        broken_lib = stub_function(original["src/lib.0"], func, body)
        if broken_lib is None:
            failures.append((name, f"could not locate `pub fn {func}`"))
            continue
        broken = dict(original)
        broken["src/lib.0"] = broken_lib

        b_chk, b_test = project_passes(broken)
        if not b_chk:
            failures.append((name, "stub broke compilation (want compile-ok, test-fail)"))
            continue
        if b_test:
            failures.append((name, "stub did not make any test fail"))
            continue

        task_id = f"zero_package_edit/{name}-restore-{func}"
        row = {
            "id": task_id,
            "title": f"Restore `{func}` in the {name} package",
            "family": "zero_package_edit",
            "split": "train",
            "difficulty": 3,
            "tags": ["zero", "package", "tests", name],
            "prompt": (
                f"The Zero package `{name}` has failing unit tests. The function "
                f"`{func}` in `src/lib.0` was replaced with an incorrect stub. "
                f"Edit `src/lib.0` so that `zero test` passes again, keeping the rest "
                f"of the package unchanged.\n\n"
                "Respond with ONLY the full corrected contents of `src/lib.0`."
            ),
            "starter_files": broken,
            "expected": {"tests_pass": True},
            "grader": {
                "type": "zero_package_edit", "entry_file": "src/lib.0", "timeout_sec": 120,
                "reward_version": "v1", "hidden": False, "check": True, "run": True, "test": True,
            },
            "environment": {"type": "local", "requires_network": False, "requires_gpu": False},
            "provenance": {
                "source": "zerolang-examples", "source_path": f"projects/{name}",
                "license": "MIT", "zero_version": ZERO_VERSION,
            },
            "_fixture": {"src/lib.0": original["src/lib.0"]},  # oracle edit
        }
        row["provenance"]["content_hash"] = common.content_hash(
            {k: row[k] for k in ("id", "prompt", "starter_files", "_fixture")}
        )
        rows.append(row)

    common.stratified_splits(rows)
    counts = common.split_and_write(rows, "zero_package_edit", "package")
    print(f"zero_package_edit: {len(rows)} verified tasks, {len(failures)} failed; splits={counts}")
    for name, diag in failures:
        print(f"  FAILED {name}: {diag}")
    return rows


if __name__ == "__main__":
    main()
