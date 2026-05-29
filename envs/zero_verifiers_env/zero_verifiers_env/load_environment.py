"""Prime `verifiers` entry point for the Zero RL environment.

    load_environment(family="zero_native", split="train", ...)

Modes
-----
* Zero-native / repair / package-edit: a single-turn environment that hands the
  model the prompt, extracts Zero source from the completion, writes it to a
  workspace, and scores it with the deterministic `zero` toolchain grader.
* Harbor-backed (`family="harbor_env"`): delegates to Prime's HarborTaskset,
  loading Harbor-format task dirs from this package's `tasks/harbor/` directory.
  Harbor owns sandboxing and test scoring (reward.json / reward.txt); we do not
  re-implement it. (No Harbor tasks ship in the pilot — see tasks/harbor/README.)

`verifiers` is imported lazily so this module is importable for unit checks even
where the framework is not installed.
"""
from __future__ import annotations

from . import rewards, taskset

ZERO_FAMILIES = {"zero_native", "zero_repair", "zero_package_edit"}

SYSTEM_PROMPT = (
    "You are an expert Zero (zerolang) programmer. Zero uses `.0` source files, "
    "typed functions, `let`/`var`, `while`, `if`/`else`, and capability passing "
    "via `World`. Respond with Zero source only."
)


def _zero_reward_func(completion, info, **_):
    """verifiers reward signature: returns a float in [0, 1]."""
    text = completion if isinstance(completion, str) else _last_text(completion)
    return rewards.reward(info, text)


def _last_text(completion) -> str:
    if isinstance(completion, list) and completion:
        msg = completion[-1]
        if isinstance(msg, dict):
            return msg.get("content", "")
    return str(completion)


def load_environment(
    family: str = "zero_native",
    split: str = "train",
    dataset_root: str | None = None,
    max_examples: int | None = None,
    **kwargs,
):
    if family == "harbor_env":
        return _load_harbor(split=split, **kwargs)

    if family not in ZERO_FAMILIES:
        raise ValueError(f"unknown family {family!r}; expected one of {ZERO_FAMILIES | {'harbor_env'}}")

    import verifiers as vf  # lazy: only needed at real run time
    from datasets import Dataset

    records = taskset.load_family(family, split, dataset_root)
    if max_examples:
        records = records[:max_examples]
    dataset = Dataset.from_list(records)

    rubric = vf.Rubric(funcs=[_zero_reward_func], weights=[1.0])
    return vf.SingleTurnEnv(
        dataset=dataset,
        system_prompt=SYSTEM_PROMPT,
        rubric=rubric,
        **kwargs,
    )


def _load_harbor(split: str = "train", **kwargs):
    """Delegate to Prime's HarborTaskset over this package's tasks/harbor dir."""
    import os

    from verifiers.integrations.harbor import HarborTaskset  # type: ignore

    here = os.path.dirname(os.path.abspath(__file__))
    tasks_dir = os.path.join(os.path.dirname(here), "tasks", "harbor")
    return HarborTaskset(tasks_dir=tasks_dir, split=split, **kwargs)
