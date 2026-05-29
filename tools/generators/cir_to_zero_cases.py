"""Emit datasets/zero_native/cases.generated.ts from the native CIR rows.

A derived artifact matching zerolang's EvalCase shape (source-of-truth stays
JSONL). Regenerated, never hand-edited.
"""
from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common


def ts_string(s: str) -> str:
    return json.dumps(s)  # JSON string literals are valid TS string literals


def main():
    rows = []
    for split in ("train", "val", "test"):
        p = os.path.join(common.ROOT, "datasets", "zero_native", f"cases.{split}.jsonl")
        if os.path.exists(p):
            rows += [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]

    lines = [
        "// AUTO-GENERATED from datasets/cir by tools/generators/cir_to_zero_cases.py.",
        "// Source of truth is the JSONL; do not edit by hand.",
        "export interface EvalCase {",
        "  id: string;",
        "  title: string;",
        "  prompt: string;",
        "  fixtureSource: string;",
        "  expectedStdout: string;",
        "  requiredSourcePatterns: RegExp[];",
        "}",
        "",
        "export const cases: EvalCase[] = [",
    ]
    for r in rows:
        fixture = r.get("_fixture", {}).get("main.0", "")
        pats = ", ".join("new RegExp(" + ts_string(p) + ")" for p in r["expected"].get("source_patterns", []))
        lines += [
            "  {",
            f"    id: {ts_string(r['id'])},",
            f"    title: {ts_string(r['title'])},",
            f"    prompt: {ts_string(r['prompt'])},",
            f"    fixtureSource: {ts_string(fixture)},",
            f"    expectedStdout: {ts_string(r['expected'].get('stdout', ''))},",
            f"    requiredSourcePatterns: [{pats}],",
            "  },",
        ]
    lines += ["];", ""]

    out = os.path.join(common.ROOT, "datasets", "zero_native", "cases.generated.ts")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"wrote {out} ({len(rows)} cases)")


if __name__ == "__main__":
    main()
