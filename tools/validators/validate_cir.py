"""Lightweight CIR validator (no external deps).

Checks the rules from tools/schema/cir.schema.json that matter for a clean
handoff: required keys, enum values, unique ids, compilable regexes, provenance
present, and that the oracle answer never leaks into the prompt.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAMILIES = {"zero_native", "zero_repair", "zero_package_edit", "harbor_env"}
SPLITS = {"train", "val", "test"}
GRADERS = {"zero_compiler_runtime", "zero_repair", "zero_package_edit", "harbor_reward"}
REQUIRED = ["id", "title", "family", "split", "difficulty", "prompt", "expected", "grader", "environment", "provenance"]


def validate_rows(rows: list[dict]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for i, r in enumerate(rows):
        tag = r.get("id", f"row[{i}]")
        for key in REQUIRED:
            if key not in r:
                errors.append(f"{tag}: missing required key '{key}'")
        if r.get("id") in seen:
            errors.append(f"{tag}: duplicate id")
        seen.add(r.get("id"))
        if r.get("family") not in FAMILIES:
            errors.append(f"{tag}: bad family {r.get('family')!r}")
        if r.get("split") not in SPLITS:
            errors.append(f"{tag}: bad split {r.get('split')!r}")
        if not isinstance(r.get("difficulty"), int) or not (1 <= r.get("difficulty", 0) <= 5):
            errors.append(f"{tag}: difficulty must be int 1..5")
        g = r.get("grader", {})
        if g.get("type") not in GRADERS:
            errors.append(f"{tag}: bad grader.type {g.get('type')!r}")
        if "reward_version" not in g:
            errors.append(f"{tag}: grader.reward_version missing")
        exp = r.get("expected", {})
        for p in exp.get("source_patterns", []) + exp.get("forbidden_patterns", []):
            try:
                re.compile(p)
            except re.error as e:
                errors.append(f"{tag}: bad regex {p!r}: {e}")
        prov = r.get("provenance", {})
        if "source" not in prov or "license" not in prov:
            errors.append(f"{tag}: provenance.source/license required")
        # The oracle fix must never appear in the prompt shown to the model.
        fixture = r.get("_fixture", {})
        for content in fixture.values():
            body = content.strip()
            if len(body) > 40 and body in r.get("prompt", ""):
                errors.append(f"{tag}: oracle fixture leaked into prompt")
        # Source files must be UTF-8 strings.
        for fn, content in {**r.get("starter_files", {}), **fixture}.items():
            if not isinstance(content, str):
                errors.append(f"{tag}: file {fn} is not a string")
    return errors


def main():
    paths = sorted(glob.glob(os.path.join(ROOT, "datasets", "cir", "tasks.*.jsonl")))
    if not paths:
        print("no CIR files found; run assemble_cir.py first", file=sys.stderr)
        return 1
    total = 0
    all_errors: list[str] = []
    for p in paths:
        rows = [json.loads(line) for line in open(p, encoding="utf-8") if line.strip()]
        total += len(rows)
        all_errors += validate_rows(rows)
    # cross-file id uniqueness
    everything = []
    for p in paths:
        everything += [json.loads(line) for line in open(p, encoding="utf-8") if line.strip()]
    all_errors += [e for e in validate_rows(everything) if "duplicate id" in e]

    if all_errors:
        print(f"CIR VALIDATION FAILED: {len(all_errors)} error(s) across {total} rows")
        for e in all_errors[:50]:
            print("  -", e)
        return 1
    print(f"CIR validation OK: {total} rows, schema/enum/regex/provenance all valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
