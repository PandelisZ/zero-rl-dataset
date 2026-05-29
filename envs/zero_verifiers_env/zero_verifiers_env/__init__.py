"""Zero RL verifiers environment.

Exposes `load_environment` for Prime Intellect hosted training / eval.
"""
from .load_environment import load_environment  # noqa: F401

__all__ = ["load_environment"]
__version__ = "0.1.0"
