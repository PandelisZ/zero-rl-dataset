"""Reward function for the Prime `verifiers` environment.

Bridges a model completion (raw text) to the deterministic Zero grader:
extract source -> build a submission -> call zero_grader.grade -> return reward.

The grader and runner are vendored from tools/graders. When this package is
uploaded to the Prime Hub standalone, copy tools/graders/{zero_grader,
zero_runner,zero_reward}.py next to this file (see env README). For local runs
from the repo we add the repo path automatically.
"""
from __future__ import annotations

import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
# repo-local fallback so `prime eval` run from the repo finds the grader
_REPO_GRADERS = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "tools", "graders"))
for _p in (_HERE, _REPO_GRADERS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import zero_grader  # noqa: E402

_FENCE = re.compile(r"```(?:zero|0|rust)?\s*\n(.*?)```", re.DOTALL)


def extract_source(text: str) -> str:
    """Pull Zero source out of a completion: prefer a fenced block, else raw."""
    blocks = _FENCE.findall(text or "")
    if blocks:
        # take the longest fenced block (most likely the full program)
        return max(blocks, key=len).strip() + "\n"
    return (text or "").strip() + "\n"


def submission_from_completion(task: dict, completion: str) -> dict:
    entry = task.get("grader", {}).get("entry_file", "main.0")
    return {"files": {entry: extract_source(completion)}}


def score(task: dict, completion: str) -> dict:
    """Full grader result for a completion. reward is result['reward']."""
    return zero_grader.grade(task, submission_from_completion(task, completion))


def reward(task: dict, completion: str) -> float:
    return score(task, completion)["reward"]
