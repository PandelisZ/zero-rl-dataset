"""Generate verified `zero_repair` tasks (before/after states).

Each task takes a known-good native fixture, applies ONE breakage transform to
produce a "before" state, and verifies that:
  * the before state genuinely fails `zero check` (and records its diagnostics)
  * the original source (the oracle "after") still compiles + runs
The model's job is to turn the before state back into a compiling, correct
program. The oracle fix is the original source.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import gen_zero_native as native

ZERO_VERSION = common.zero_runner.zero_version()
DIAG_CODE = re.compile(r"\b[A-Z]{3}\d{3}\b")


def brk_drop_raises(src: str):
    if "-> Void raises {" in src:
        return src.replace("-> Void raises {", "-> Void {", 1), "drop_raises", \
            "main is no longer marked `raises` but still calls fallible operations with `check`"
    return None


def brk_drop_check(src: str):
    idx = src.find("    check ")
    if idx != -1:
        broken = src[:idx] + "    " + src[idx + len("    check "):]
        return broken, "drop_check", "a fallible call is invoked without `check`"
    return None


def brk_wrong_return(src: str):
    if "-> u32 {" in src:
        return src.replace("-> u32 {", "-> Bool {", 1), "wrong_return_type", \
            "a helper's return type was changed to Bool but it returns u32"
    return None


def brk_rename_call(src: str):
    for name in ["factorial", "fib", "gcd", "is_prime"]:
        # rename the *call* (not the definition) by typo-ing the last occurrence
        calls = [m.start() for m in re.finditer(re.escape(name + "("), src)]
        defs = [m.start() for m in re.finditer(re.escape("fn " + name + "("), src)]
        call_sites = [c for c in calls if not any(c == d + 3 for d in defs)]
        if call_sites:
            at = call_sites[-1]
            broken = src[:at] + name + "x" + src[at + len(name):]
            return broken, "unbound_call", f"call to `{name}` was misspelled as `{name}x`"
    return None


BREAKERS = [brk_drop_raises, brk_drop_check, brk_wrong_return, brk_rename_call]


def main():
    rows = []
    failures = []
    # Rotate breakers across fixtures for variety; fall back to the next
    # applicable breaker if the chosen one does not apply.
    for i, (slug, title, diff, tags, prompt, src, extra) in enumerate(native.specs()):
        ok, stdout, _ = common.run_fixture({"main.0": src})
        if not ok:
            continue  # only break fixtures we know are good
        order = BREAKERS[i % len(BREAKERS):] + BREAKERS[: i % len(BREAKERS)]
        broken = None
        for fn in order:
            broken = fn(src)
            if broken:
                break
        if not broken:
            continue
        broken_src, kind, human = broken

        # Verify the before-state actually fails to compile.
        ws = common.zero_runner.materialize({"main.0": broken_src})
        try:
            chk = common.zero_runner.check(ws, "main.0", 60)
        finally:
            import shutil
            shutil.rmtree(ws, ignore_errors=True)
        if chk.ok:
            failures.append((slug, kind, "breakage did not break compilation"))
            continue
        errors = sorted(set(DIAG_CODE.findall(chk.stderr or chk.stdout)))

        task_id = f"zero_repair/{slug}--{kind}"
        row = {
            "id": task_id,
            "title": f"Repair: {title} ({kind})",
            "family": "zero_repair",
            "split": "train",
            "difficulty": min(5, diff + 1),
            "tags": ["zero", "repair"] + tags,
            "prompt": (
                f"The following Zero program does not compile: {human}. "
                f"Fix it so it compiles and runs correctly. Original task: {prompt}\n\n"
                f"```zero\n{broken_src}```\n\n"
                "Respond with ONLY the corrected Zero source for `main.0`."
            ),
            "starter_files": {"main.0": broken_src},
            "expected": {
                "stdout": stdout,
                "source_patterns": [native.PAT_MAIN, native.PAT_WRITE],
                "forbidden_patterns": common.FORBIDDEN_DEFAULT,
            },
            "repair_objective": {"initial_expected_errors": errors, "target": "compile_and_run"},
            "grader": {
                "type": "zero_repair", "entry_file": "main.0", "timeout_sec": 60,
                "reward_version": "v1", "hidden": False,
                "check": True, "run": True, "stdout_exact": True, "patterns": True,
            },
            "environment": {"type": "local", "requires_network": False, "requires_gpu": False},
            "provenance": {
                "source": "generated", "source_path": "tools/generators/gen_zero_repair.py",
                "license": "MIT", "zero_version": ZERO_VERSION,
            },
            "_fixture": {"main.0": src},  # oracle fix
        }
        row["provenance"]["content_hash"] = common.content_hash(
            {k: row[k] for k in ("id", "prompt", "starter_files", "expected", "_fixture")}
        )
        rows.append(row)

    common.stratified_splits(rows)
    counts = common.split_and_write(rows, "zero_repair", "repair")
    print(f"zero_repair: {len(rows)} verified tasks, {len(failures)} failed; splits={counts}")
    for slug, kind, diag in failures:
        print(f"  FAILED {slug} [{kind}]: {diag}")
    return rows


if __name__ == "__main__":
    main()
