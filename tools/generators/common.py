"""Shared helpers for the Zero RL task generators."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "graders"))
import zero_runner  # noqa: E402

FORBIDDEN_DEFAULT = [r"std\.fs", r"std\.proc", r"std\.net", r"std\.http"]

# Reusable decimal formatter (the corpus idiom; needed for any numeric output).
FMT_U32 = """pub fn fmt_u32(buf: MutSpan<u8>, value: u32) -> Span<u8> {
    if value == 0 {
        buf[0] = 48
        return buf[0..1]
    }
    var n: u32 = value
    var tmp: [10]u8 = [0; 10]
    var count: usize = 0
    while n > 0 {
        tmp[count] = 48 + ((n % 10) as u8)
        n = n / 10
        count = count + 1
    }
    var i: usize = 0
    while i < count {
        buf[i] = tmp[count - 1 - i]
        i = i + 1
    }
    return buf[0..count]
}
"""


def content_hash(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def split_for(task_id: str) -> str:
    """Deterministic 80/10/10 train/val/test split keyed on the task id."""
    h = int(hashlib.sha256(task_id.encode()).hexdigest(), 16) % 100
    if h < 80:
        return "train"
    if h < 90:
        return "val"
    return "test"


def stratified_splits(rows: list[dict]) -> list[dict]:
    """Balanced, deterministic 80/10/10 split by sorted-id position.

    Avoids the variance of hashing on small pilot sets so val/test are never
    starved. Mutates each row's "split" in place and returns the list.
    """
    for idx, r in enumerate(sorted(rows, key=lambda x: x["id"])):
        m = idx % 10
        r["split"] = "val" if m == 8 else ("test" if m == 9 else "train")
    return rows


def run_fixture(files: dict, entry: str = "main.0", project: bool = False, args=None):
    """Compile + run a fixture. Returns (ok, stdout, diagnostics)."""
    ws = zero_runner.materialize(files)
    try:
        target = "." if project else entry
        chk = zero_runner.check(ws, target, 60)
        if not chk.ok:
            return False, "", f"check failed: {(chk.stderr or chk.stdout).strip()[:300]}"
        rn = zero_runner.run(ws, target, 60, args=args)
        if not rn.ok:
            return False, rn.stdout, f"run failed: {(rn.stderr or rn.stdout).strip()[:300]}"
        return True, rn.stdout, ""
    finally:
        import shutil

        shutil.rmtree(ws, ignore_errors=True)


def write_jsonl(path: str, rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def split_and_write(rows: list[dict], family_dir: str, prefix: str) -> dict:
    by_split: dict[str, list[dict]] = {"train": [], "val": [], "test": []}
    for r in rows:
        by_split[r["split"]].append(r)
    counts = {}
    for split, items in by_split.items():
        path = os.path.join(ROOT, "datasets", family_dir, f"{prefix}.{split}.jsonl")
        write_jsonl(path, items)
        counts[split] = len(items)
    return counts
