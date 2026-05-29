"""Zero RL verifiers environment.

Exposes `load_environment` plus per-family loaders so each registered env id
(zero_native / zero_repair / zero_package_edit / harbor_env) resolves to the
correct family for Prime.
"""
from .load_environment import load_environment  # noqa: F401


def load_zero_native(**kwargs):
    return load_environment(family="zero_native", **kwargs)


def load_zero_repair(**kwargs):
    return load_environment(family="zero_repair", **kwargs)


def load_zero_package_edit(**kwargs):
    return load_environment(family="zero_package_edit", **kwargs)


def load_harbor_env(**kwargs):
    return load_environment(family="harbor_env", **kwargs)


__all__ = [
    "load_environment",
    "load_zero_native",
    "load_zero_repair",
    "load_zero_package_edit",
    "load_harbor_env",
]
__version__ = "0.2.0"
