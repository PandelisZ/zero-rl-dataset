"""Reward rubric for `zero_graph_edit` tasks.

The behavior being trained is the CHECKED ProgramGraph edit, not text editing.
Most of the weight requires the graph-patch surface: a `zerolang_edit` tool call
that succeeded and reached the target program. Modeled on graphlanger's
zerolang_editing rubric, adapted to this env's Roder-aligned tools.

Weights: graph_patch_success 0.50, target_source_match 0.20,
         zero_check_pass 0.15, graph_surface_used 0.15.
"""
from __future__ import annotations

import json
import re

try:
    import zero_runner
except ImportError:  # pragma: no cover
    from . import zero_runner


def _normalize(src: str) -> str:
    return "\n".join(line.rstrip() for line in (src or "").strip().splitlines()).strip()


def _target(info, answer: str) -> str:
    if isinstance(info, dict):
        exp = info.get("expected") or {}
        if isinstance(exp, dict) and isinstance(exp.get("target_source"), str):
            return exp["target_source"]
    if isinstance(info, str):
        try:
            d = json.loads(info)
            return (d.get("expected") or {}).get("target_source", answer or "")
        except json.JSONDecodeError:
            pass
    return answer or ""


def _msg_content(m) -> str:
    if isinstance(m, dict):
        c = m.get("content", "")
    else:
        c = getattr(m, "content", "")
    return c if isinstance(c, str) else str(c)


def _completion_text(completion) -> str:
    if isinstance(completion, str):
        return completion
    for m in reversed(completion or []):
        role = m.get("role") if isinstance(m, dict) else getattr(m, "role", None)
        if role == "assistant":
            t = _msg_content(m)
            if t:
                return t
    return _msg_content((completion or [{}])[-1]) if completion else ""


def _extract_final_source(completion) -> str:
    text = _completion_text(completion).strip()
    m = re.search(r"```json\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        text2 = m.group(1).strip()
    else:
        text2 = text
    try:
        payload = json.loads(text2)
        if isinstance(payload, dict) and isinstance(payload.get("final_source"), str):
            return payload["final_source"]
    except json.JSONDecodeError:
        pass
    fz = re.search(r"```(?:zero|0)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fz:
        return fz.group(1).strip()
    return text


def _walk_strings(value, seen=None):
    if seen is None:
        seen = set()
    if id(value) in seen:
        return
    seen.add(id(value))
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _walk_strings(v, seen)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _walk_strings(v, seen)
    else:
        md = getattr(value, "model_dump", None)
        if callable(md):
            try:
                yield from _walk_strings(md(), seen)
                return
            except Exception:
                pass
        d = getattr(value, "__dict__", None)
        if isinstance(d, dict):
            yield from _walk_strings(d, seen)


def _patched_sources(state):
    """Yield `source` strings from successful zerolang_edit tool results in state."""
    for s in _walk_strings(state or {}):
        if '"patchedGraphHash"' not in s and '"source"' not in s:
            continue
        try:
            payload = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("ok") and isinstance(payload.get("source"), str):
            yield payload["source"]


def _used_graph_surface(state, completion) -> bool:
    blob = (json.dumps(_safe(state)) + "\n" + _completion_text(completion)).lower()
    markers = ["zerolang_edit", "patchedgraphhash", "graph patch", "expect=", "set node=", "graphhash", "graph_objective"]
    return any(mk in blob for mk in markers)


def _safe(state):
    try:
        json.dumps(state)
        return state
    except (TypeError, ValueError):
        return {}


async def graph_patch_success(state=None, info=None, answer: str = "", **_) -> float:
    target = _normalize(_target(info, answer))
    for src in _patched_sources(state):
        if _normalize(src) == target:
            return 1.0
    return 0.0


async def target_source_match(completion=None, info=None, answer: str = "", **_) -> float:
    target = _normalize(_target(info, answer))
    return 1.0 if _normalize(_extract_final_source(completion)) == target else 0.0


async def zero_check_pass(completion=None, **_) -> float:
    src = _extract_final_source(completion)
    if not src.strip():
        return 0.0
    import shutil
    ws = zero_runner.materialize({"main.0": src})
    try:
        return 1.0 if zero_runner.check(ws, "main.0", 60).ok else 0.0
    finally:
        shutil.rmtree(ws, ignore_errors=True)


async def graph_surface_used(state=None, completion=None, **_) -> float:
    return 1.0 if _used_graph_surface(state, completion) else 0.0


def graph_edit_rubric():
    import verifiers as vf
    return vf.Rubric(
        funcs=[graph_patch_success, target_source_match, zero_check_pass, graph_surface_used],
        weights=[0.50, 0.20, 0.15, 0.15],
    )
