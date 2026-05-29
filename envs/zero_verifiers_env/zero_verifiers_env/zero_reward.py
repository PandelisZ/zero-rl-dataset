"""Reward shaping (v1) for Zero RL tasks.

Pure functions over a metrics dict so the formulas are easy to audit, version,
and unit-test independently of the toolchain. Each returns a scalar in [0, 1].
"""
from __future__ import annotations

REWARD_VERSION = "v1"


def native_reward(m: dict) -> float:
    """zero_native: format / check / run / stdout / patterns / forbidden / style."""
    if m.get("hard_zero"):
        return 0.0
    return (
        0.05 * m.get("format_valid", 0.0)
        + 0.25 * m.get("zero_check", 0.0)
        + 0.20 * m.get("zero_run", 0.0)
        + 0.25 * m.get("stdout_match", 0.0)
        + 0.15 * m.get("required_patterns", 0.0)
        + 0.05 * m.get("forbidden_patterns", 0.0)
        + 0.05 * m.get("style_or_size", 0.0)
    )


def repair_reward(m: dict) -> float:
    """zero_repair: source-only / error-reduction / check / run / stdout / minimality."""
    if m.get("hard_zero"):
        return 0.0
    return (
        0.10 * m.get("format_valid", 0.0)
        + 0.15 * m.get("compiler_error_reduction", 0.0)
        + 0.30 * m.get("zero_check", 0.0)
        + 0.20 * m.get("zero_run", 0.0)
        + 0.20 * m.get("stdout_match", 0.0)
        + 0.05 * m.get("minimality", 0.0)
    )


def package_reward(m: dict) -> float:
    """zero_package_edit: structure / check / tests pass-fraction / run."""
    if m.get("hard_zero"):
        return 0.0
    return (
        0.05 * m.get("format_valid", 0.0)
        + 0.25 * m.get("zero_check", 0.0)
        + 0.50 * m.get("tests_pass", 0.0)
        + 0.20 * m.get("zero_run", 0.0)
    )


REWARD_FNS = {
    "zero_compiler_runtime": native_reward,
    "zero_repair": repair_reward,
    "zero_package_edit": package_reward,
}
