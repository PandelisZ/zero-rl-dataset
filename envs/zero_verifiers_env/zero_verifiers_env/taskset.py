"""Task loading for the Zero verifiers environment.

Reads the canonical CIR JSONL and exposes per-family / per-split task lists.
The oracle field `_fixture` is stripped here so it can never reach the model.
Harbor-backed tasks are intentionally NOT loaded here; see load_environment for
how they are delegated to Prime's HarborTaskset.
"""
from __future__ import annotations

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
# Prefer the CIR data bundled inside the package (self-contained for Hub
# install); fall back to the repo's datasets/cir for local dev.
_BUNDLED = os.path.join(_HERE, "data", "cir")
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "datasets", "cir"))
DEFAULT_DATASET_ROOT = _BUNDLED if os.path.isdir(_BUNDLED) else _REPO


def load_cir(split: str, dataset_root: str | None = None) -> list[dict]:
    root = dataset_root or DEFAULT_DATASET_ROOT
    path = os.path.join(root, f"tasks.{split}.jsonl")
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def to_dataset_records(rows: list[dict]) -> list[dict]:
    """Shape CIR rows into prompt/info records for a verifiers dataset.

    `info` carries the full task MINUS the oracle fixture, so the reward
    function can grade while the model only ever sees `prompt`.
    """
    records = []
    for r in rows:
        info = {k: v for k, v in r.items() if k != "_fixture"}
        records.append({
            "question": r["prompt"],  # SingleTurnEnv combines this with system_prompt
            "answer": "",  # graded by execution, not string match
            "info": info,
            "task": r["family"],
        })
    return records


def load_family(family: str, split: str, dataset_root: str | None = None) -> list[dict]:
    rows = [r for r in load_cir(split, dataset_root) if r["family"] == family]
    return to_dataset_records(rows)
