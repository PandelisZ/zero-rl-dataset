"""Oracle validation: the integrity backbone of the dataset.

For every task we run the real grader on:
  * the ORACLE submission (the reference fix `_fixture`)  -> must score high
  * a BASELINE submission (no edit / broken start)        -> should score low

If an oracle does not score ~1.0, the task is unsolvable-as-graded and must be
fixed before training. If the baseline already scores high, the task is trivial
and gives no RL signal. Emits a JSON summary to reports/oracle_results.json.
"""
from __future__ import annotations

import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "graders"))
import zero_grader  # noqa: E402

ORACLE_MIN = 0.95
BASELINE_MAX = 0.80


def baseline_submission(task: dict) -> dict:
    """A non-solution: for repair/package, submit the broken start unchanged;
    for native, submit an empty program."""
    fam = task["family"]
    if fam == "zero_repair":
        return {"files": {"main.0": task["starter_files"].get("main.0", "")}}
    if fam == "zero_package_edit":
        return {"files": {}}  # no edit -> broken stub remains
    return {"files": {"main.0": "pub fn main(world: World) -> Void {\n}\n"}}


def main():
    paths = sorted(glob.glob(os.path.join(ROOT, "datasets", "cir", "tasks.*.jsonl")))
    rows = []
    for p in paths:
        rows += [json.loads(line) for line in open(p, encoding="utf-8") if line.strip()]

    results = []
    oracle_fail = []
    trivial = []
    graph_edit_skipped = 0
    for r in rows:
        # zero_graph_edit is graded by the env rubric over a tool trajectory, not
        # the deterministic file grader; its oracle (gold --op reaches a compiling
        # target) is verified at generation time. Skip here.
        if r["family"] == "zero_graph_edit":
            graph_edit_skipped += 1
            continue
        oracle = zero_grader.grade(r, {"files": r.get("_fixture", {})})
        baseline = zero_grader.grade(r, baseline_submission(r))
        results.append({
            "id": r["id"], "family": r["family"], "split": r["split"],
            "oracle_reward": oracle["reward"], "baseline_reward": baseline["reward"],
        })
        if oracle["reward"] < ORACLE_MIN:
            oracle_fail.append((r["id"], oracle["reward"], oracle.get("diagnostics", {})))
        if baseline["reward"] > BASELINE_MAX:
            trivial.append((r["id"], baseline["reward"]))

    summary = {
        "total": len(rows),
        "oracle_mean": round(sum(x["oracle_reward"] for x in results) / max(1, len(results)), 4),
        "baseline_mean": round(sum(x["baseline_reward"] for x in results) / max(1, len(results)), 4),
        "oracle_failures": len(oracle_fail),
        "trivial_tasks": len(trivial),
        "results": results,
    }
    out = os.path.join(ROOT, "reports", "oracle_results.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    print(f"graph_edit skipped   : {graph_edit_skipped} (rubric-graded; verified at generation)")
    print(f"oracle mean reward   : {summary['oracle_mean']}  (target >= {ORACLE_MIN})")
    print(f"baseline mean reward : {summary['baseline_mean']}  (target <= {BASELINE_MAX})")
    print(f"oracle failures      : {len(oracle_fail)}")
    for tid, rw, _ in oracle_fail[:20]:
        print(f"  ORACLE LOW {tid}: {rw}")
    print(f"trivial tasks        : {len(trivial)}")
    for tid, rw in trivial[:20]:
        print(f"  TRIVIAL {tid}: {rw}")
    return 1 if oracle_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
