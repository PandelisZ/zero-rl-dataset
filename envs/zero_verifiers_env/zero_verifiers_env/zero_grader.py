"""Deterministic grader for Zero RL tasks, grounded in the native toolchain.

Usage (library):
    from zero_grader import grade
    result = grade(task_dict, submission_dict)

Usage (CLI):
    python zero_grader.py task.json submission.json

`submission` is {"files": {relpath: content}}. For package tasks the submission
is overlaid on top of the task's `starter_files` workspace; for single-file
native/repair tasks the submission supplies the entry file directly.

Returns: {"reward": float, "metrics": {...}, "diagnostics": {...}}.
"""
from __future__ import annotations

import json
import re
import shutil
import sys

import zero_reward
import zero_runner

DIAG_CODE = re.compile(r"\b[A-Z]{3}\d{3}\b")


def _count_errors(text: str) -> int:
    return len(DIAG_CODE.findall(text))


def _looks_like_zero(src: str) -> bool:
    return ("fn " in src) or ("pub fn" in src)


def _pattern_fraction(source: str, patterns: list[str]) -> float:
    if not patterns:
        return 1.0
    hits = sum(1 for p in patterns if re.search(p, source) is not None)
    return hits / len(patterns)


def _no_forbidden(source: str, patterns: list[str]) -> float:
    if not patterns:
        return 1.0
    return 0.0 if any(re.search(p, source) for p in patterns) else 1.0


def grade(task: dict, submission: dict) -> dict:
    grader = task.get("grader", {})
    gtype = grader.get("type", "zero_compiler_runtime")
    timeout = int(grader.get("timeout_sec", 60))
    entry = grader.get("entry_file", "main.0")
    expected = task.get("expected", {})

    sub_files = (submission or {}).get("files", {}) or {}
    files = {**task.get("starter_files", {}), **sub_files}

    diagnostics: dict = {}
    metrics: dict = {
        "format_valid": 0.0,
        "zero_check": 0.0,
        "zero_run": 0.0,
        "stdout_match": 0.0,
        "required_patterns": 0.0,
        "forbidden_patterns": 1.0,
        "style_or_size": 0.0,
        "tests_pass": 0.0,
        "compiler_error_reduction": 0.0,
        "minimality": 0.0,
        "timeout": 0.0,
        "hard_zero": False,
    }

    # Hard-zero: nothing usable submitted.
    if not files or (entry not in files and not zero_runner.is_project(files)):
        metrics["hard_zero"] = True
        return {"reward": 0.0, "metrics": metrics, "diagnostics": {"error": "no submission / missing entry file"}}

    all_source = "\n".join(v for k, v in files.items() if k.endswith(".0"))
    entry_source = files.get(entry, "")
    metrics["format_valid"] = 1.0 if _looks_like_zero(entry_source or all_source) else 0.0

    project_mode = zero_runner.is_project(files)
    workspace = zero_runner.materialize(files)
    try:
        target = "." if project_mode else entry

        chk = zero_runner.check(workspace, target, timeout)
        metrics["zero_check"] = 1.0 if chk.ok else 0.0
        diagnostics["compiler_stderr"] = (chk.stderr or chk.stdout)[:4000]
        if chk.timed_out:
            metrics["timeout"] = 1.0
            metrics["hard_zero"] = True

        # Pattern checks operate on submitted source regardless of compile result.
        metrics["required_patterns"] = _pattern_fraction(all_source, expected.get("source_patterns", []))
        metrics["forbidden_patterns"] = _no_forbidden(all_source, expected.get("forbidden_patterns", []))

        if gtype == "zero_package_edit":
            tst = zero_runner.test(workspace, target, timeout)
            passed, total = zero_runner.parse_test_counts(tst.stdout, tst.stderr)
            metrics["tests_pass"] = 1.0 if (tst.ok and passed > 0) else 0.0
            metrics["tests_passed"] = passed
            diagnostics["test_output"] = (tst.stdout or tst.stderr)[:4000]
            rn = zero_runner.run(workspace, target, timeout)
            metrics["zero_run"] = 1.0 if rn.ok else 0.0
            metrics["style_or_size"] = metrics["zero_check"]
        else:
            rn = zero_runner.run(workspace, target, timeout)
            metrics["zero_run"] = 1.0 if rn.ok else 0.0
            diagnostics["runtime_stderr"] = (rn.stderr)[:4000]
            diagnostics["stdout"] = rn.stdout[:4000]
            if rn.timed_out:
                metrics["timeout"] = 1.0
                metrics["hard_zero"] = True
            if "stdout" in expected:
                metrics["stdout_match"] = 1.0 if rn.stdout == expected["stdout"] else 0.0
            else:
                metrics["stdout_match"] = metrics["zero_run"]
            metrics["style_or_size"] = 1.0 if (chk.ok and len(all_source) < 4000) else 0.0

        # Repair-specific: reward shrinking the diagnostic count vs the broken start.
        if gtype == "zero_repair":
            starter = task.get("starter_files", {})
            before_ws = zero_runner.materialize(starter)
            try:
                before_chk = zero_runner.check(before_ws, entry if not zero_runner.is_project(starter) else ".", timeout)
            finally:
                shutil.rmtree(before_ws, ignore_errors=True)
            before_errs = _count_errors(before_chk.stderr or before_chk.stdout)
            after_errs = _count_errors(chk.stderr or chk.stdout)
            if metrics["zero_check"] == 1.0:
                metrics["compiler_error_reduction"] = 1.0
            elif before_errs > 0:
                metrics["compiler_error_reduction"] = max(0.0, min(1.0, (before_errs - after_errs) / before_errs))
            base_len = max(1, len(starter.get(entry, "")))
            ratio = len(entry_source) / base_len
            metrics["minimality"] = 1.0 if 0.5 <= ratio <= 2.0 else 0.5
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    reward_fn = zero_reward.REWARD_FNS.get(gtype, zero_reward.native_reward)
    reward = round(reward_fn(metrics), 4)
    return {"reward": reward, "metrics": metrics, "diagnostics": diagnostics}


def _main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: python zero_grader.py <task.json> <submission.json>", file=sys.stderr)
        return 2
    with open(argv[1]) as fh:
        task = json.load(fh)
    with open(argv[2]) as fh:
        submission = json.load(fh)
    print(json.dumps(grade(task, submission), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
