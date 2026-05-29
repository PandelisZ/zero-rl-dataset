"""Merge all per-family case files into the canonical CIR (source of truth).

Writes datasets/cir/tasks.{train,val,test}.jsonl and a dataset_manifest.json
summarizing counts by family / split / difficulty.
"""
from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

FAMILY_GLOBS = {
    "zero_native": "datasets/zero_native/cases.{split}.jsonl",
    "zero_repair": "datasets/zero_repair/repair.{split}.jsonl",
    "zero_package_edit": "datasets/zero_package_edit/package.{split}.jsonl",
}


def main():
    manifest = {"families": {}, "splits": {}, "difficulty": {}, "total": 0}
    for split in ("train", "val", "test"):
        rows = []
        for family, pat in FAMILY_GLOBS.items():
            path = os.path.join(common.ROOT, pat.format(split=split))
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        rows.append(json.loads(line))
        common.write_jsonl(os.path.join(common.ROOT, "datasets", "cir", f"tasks.{split}.jsonl"), rows)
        manifest["splits"][split] = len(rows)
        for r in rows:
            manifest["families"][r["family"]] = manifest["families"].get(r["family"], 0) + 1
            d = str(r["difficulty"])
            manifest["difficulty"][d] = manifest["difficulty"].get(d, 0) + 1
            manifest["total"] += 1

    out = os.path.join(common.ROOT, "datasets", "manifests", "dataset_manifest.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
