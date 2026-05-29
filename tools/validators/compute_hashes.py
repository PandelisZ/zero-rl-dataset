"""Content-hash every dataset artifact for reproducibility/provenance.

Writes datasets/manifests/hashes.json mapping repo-relative path -> sha256.
"""
from __future__ import annotations

import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TARGET_DIRS = ["datasets", "tools", "envs", "prime"]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    hashes = {}
    for d in TARGET_DIRS:
        base = os.path.join(ROOT, d)
        for dirpath, _, filenames in os.walk(base):
            if "__pycache__" in dirpath:
                continue
            for fn in sorted(filenames):
                if fn.endswith((".pyc",)):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, ROOT)
                hashes[rel] = sha256_file(full)
    out = os.path.join(ROOT, "datasets", "manifests", "hashes.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    payload = {"file_count": len(hashes), "files": dict(sorted(hashes.items()))}
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print(f"hashed {len(hashes)} files -> datasets/manifests/hashes.json")


if __name__ == "__main__":
    main()
