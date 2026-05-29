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
    harness: str = "deterministic",
    **kwargs,
):
    """Build the Zero RL environment.

    harness:
      * "deterministic" (default) — single-turn: the model emits Zero source,
        scored locally by the native `zero` toolchain grader. No sandbox; fully
        verified offline.
      * "roder-zero" — sandboxed agentic editing: the Roder agent edits the
        zerolang project inside a Prime sandbox that has `zero` + `roder`
        installed (see sandbox/ + roder_zero.py), scored by score.sh. Requires
        verifiers + a linux/amd64 sandbox.
    """
    if family == "harbor_env":
        return _load_harbor(split=split, **kwargs)

    if family not in ZERO_FAMILIES:
        raise ValueError(f"unknown family {family!r}; expected one of {ZERO_FAMILIES | {'harbor_env'}}")

    if harness in ("roder-zero", "zero-roder"):
        return _load_roder_zero(family=family, split=split, dataset_root=dataset_root,
                                max_examples=max_examples, **kwargs)

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


def _load_roder_zero(
    family: str,
    split: str,
    dataset_root: str | None,
    max_examples: int | None,
    docker_image: str = "zero-roder-sandbox:latest",
    roder_binary_url: str | None = None,
    roder_config_url: str | None = None,
    roder_soft_timeout_sec: int = 900,
    **kwargs,
):
    """Sandboxed agentic editing with Roder as the harness.

    Mirrors graphlanger's `harbor_terminal_bench` roder-zero assembly: a
    SandboxTaskSet (one zerolang project per task, scored by score.sh emitting
    reward.json) composed with the RoderZero harness via ComposableEnv. The
    sandbox image is built from sandbox/Dockerfile (installs zero + roder).

    Validate on Prime/amd64 with `prime eval run` — it cannot run on this host
    (darwin/arm64, no Roder binary).
    """
    from .roder_zero import RoderZero

    rkwargs = {"soft_timeout_sec": roder_soft_timeout_sec}
    if roder_binary_url:
        rkwargs["binary_url"] = roder_binary_url
    if roder_config_url:
        rkwargs["config_url"] = roder_config_url
    harness = RoderZero(**rkwargs)

    records = taskset.load_family(family, split, dataset_root)
    if max_examples:
        records = records[:max_examples]

    try:
        from verifiers.v1 import ComposableEnv, SandboxSpec, SandboxTaskSet
    except Exception as exc:  # pragma: no cover - depends on installed verifiers
        raise RuntimeError(
            "roder-zero needs verifiers.v1 (ComposableEnv/SandboxTaskSet/SandboxSpec). "
            "Install verifiers>=0.1.14 and run on a linux/amd64 Prime sandbox. "
            "Reference assembly: graphlanger environments/harbor_terminal_bench."
        ) from exc

    spec = SandboxSpec(image=docker_image, timeout_minutes=20)
    taskset_obj = SandboxTaskSet(
        dataset=records,
        sandbox_spec=spec,
        rubric=_reward_json_rubric(),
    )
    return ComposableEnv(taskset=taskset_obj, harness=harness, **kwargs)


def _reward_json_rubric():
    """Rubric that reads the reward score.sh writes to /logs/verifier/reward.json."""
    import verifiers as vf

    def reward_from_sandbox(state, **_):
        try:
            return float(state.get("verifier_reward", 0.0))
        except Exception:
            return 0.0

    return vf.Rubric(funcs=[reward_from_sandbox], weights=[1.0])


def _load_harbor(split: str = "train", **kwargs):
    """Delegate to Prime's HarborTaskset over this package's tasks/harbor dir."""
    import os

    from verifiers.integrations.harbor import HarborTaskset  # type: ignore

    here = os.path.dirname(os.path.abspath(__file__))
    tasks_dir = os.path.join(os.path.dirname(here), "tasks", "harbor")
    return HarborTaskset(tasks_dir=tasks_dir, split=split, **kwargs)
