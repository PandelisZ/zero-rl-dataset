"""Standalone harness for local sanity checks without the verifiers framework.

`prime eval` / `prime rl` drive the environment through load_environment. This
module lets you exercise the exact scoring path offline:

    python -m zero_verifiers_env.harness zero_native val
"""
from __future__ import annotations

import sys

from . import rewards, taskset


def run(family: str, split: str, dataset_root: str | None = None) -> dict:
    """Score every task's ORACLE fixture as a self-test of the scoring path."""
    rows = taskset.load_cir(split, dataset_root)
    rows = [r for r in rows if r["family"] == family]
    total = 0.0
    n = 0
    for r in rows:
        # reconstruct a completion that wraps the oracle fixture in a fence
        entry = r.get("grader", {}).get("entry_file", "main.0")
        src = r.get("_fixture", {}).get(entry, "")
        completion = f"```zero\n{src}```"
        total += rewards.reward(r, completion)
        n += 1
    return {"family": family, "split": split, "n": n, "oracle_mean_reward": round(total / max(1, n), 4)}


if __name__ == "__main__":
    fam = sys.argv[1] if len(sys.argv) > 1 else "zero_native"
    spl = sys.argv[2] if len(sys.argv) > 2 else "val"
    print(run(fam, spl))
