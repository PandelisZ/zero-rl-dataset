"""Generate verified `zero_package_edit` tasks from the demo projects.

Auto-discovers every project under ../zerolang-examples/projects and, for each,
stubs one or more tested functions in lib.0 with a type-correct but WRONG return
so the project still passes `zero check` but FAILS `zero test`. The model must
restore correct behaviour; the oracle is the original project.

Verified per task: original compiles + passes tests; stub compiles + fails tests.
"""
from __future__ import annotations

import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

ZERO_VERSION = common.zero_runner.zero_version()
EXAMPLES = os.path.abspath(os.path.join(common.ROOT, "..", "zerolang-examples", "projects"))

MAX_PER_PROJECT = 3
# Candidate wrong-return constants by declared return type (tried in order).
WRONG_RETURNS = {
    "Bool": ["    return false\n", "    return true\n"],
    "u32": ["    return 0_u32\n", "    return 1_u32\n"],
    "i32": ["    return 0\n", "    return -1\n"],
    "u8": ["    return 0_u8\n", "    return 1_u8\n"],
    "usize": ["    return 0\n", "    return 1\n"],
}
PUBFN = re.compile(r"pub fn (\w+)\s*\([^)]*\)\s*->\s*([A-Za-z0-9_]+)\s*\{")


def stub_function(src: str, name: str, new_body: str) -> str | None:
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


def read_project(name: str) -> dict | None:
    base = os.path.join(EXAMPLES, name)
    files = {}
    for rel in ("zero.json", "src/main.0", "src/lib.0"):
        p = os.path.join(base, rel)
        if not os.path.exists(p):
            return None
        with open(p, encoding="utf-8") as fh:
            files[rel] = fh.read()
    return files


def project_passes(files: dict) -> tuple[bool, bool]:
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


def candidate_functions(lib: str) -> list[tuple[str, str]]:
    """(name, return_type) for pub fns with a stubbable scalar return type."""
    out = []
    for m in PUBFN.finditer(lib):
        name, ret = m.group(1), m.group(2)
        if ret in WRONG_RETURNS and name not in {"fmt_u32"}:
            out.append((name, ret))
    return out


def make_task(name: str, func: str, original: dict, broken_lib: str) -> dict:
    broken = dict(original)
    broken["src/lib.0"] = broken_lib
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
            f"`{func}` in `src/lib.0` was replaced with an incorrect stub. Edit "
            f"`src/lib.0` so that `zero test` passes again, keeping the rest of "
            f"the package unchanged.\n\n"
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
        "_fixture": {"src/lib.0": original["src/lib.0"]},
    }
    row["provenance"]["content_hash"] = common.content_hash(
        {k: row[k] for k in ("id", "prompt", "starter_files", "_fixture")}
    )
    return row


def main():
    rows = []
    failures = []
    projects = sorted(
        d for d in os.listdir(EXAMPLES)
        if os.path.isdir(os.path.join(EXAMPLES, d)) and not d.startswith(".")
    )
    for name in projects:
        original = read_project(name)
        if original is None:
            failures.append((name, "missing zero.json/main.0/lib.0"))
            continue
        ok_chk, ok_test = project_passes(original)
        if not (ok_chk and ok_test):
            failures.append((name, "original does not pass check+test"))
            continue

        made = 0
        for func, ret in candidate_functions(original["src/lib.0"]):
            if made >= MAX_PER_PROJECT:
                break
            chosen = None
            for body in WRONG_RETURNS[ret]:
                broken_lib = stub_function(original["src/lib.0"], func, body)
                if broken_lib is None:
                    continue
                broken = dict(original)
                broken["src/lib.0"] = broken_lib
                b_chk, b_test = project_passes(broken)
                if b_chk and not b_test:
                    chosen = broken_lib
                    break
            if chosen is not None:
                rows.append(make_task(name, func, original, chosen))
                made += 1
        if made == 0:
            failures.append((name, "no stub broke a test"))

    common.stratified_splits(rows)
    counts = common.split_and_write(rows, "zero_package_edit", "package")
    print(f"zero_package_edit: {len(rows)} verified tasks from {len(projects)} projects; splits={counts}")
    for name, diag in failures:
        print(f"  NOTE {name}: {diag}")
    return rows


if __name__ == "__main__":
    main()
