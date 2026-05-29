"""Zero-coder tools, aligned with Roder's `roder-ext-zerolang` tool surface.

These mirror the seven model-facing tools Roder exposes (same names, semantics,
and underlying `zero` argv) so a policy trained here transfers to the Roder
harness:

    zerolang_skills_get   zero skills get <skill> [--full]
    zerolang_check        zero check --json [--target][--emit] <input>
    zerolang_graph_dump   zero graph dump --json [--target] <input>
    zerolang_graph_view   zero graph view --json [--target] <input>
    zerolang_fix_plan     zero fix --plan --json [--target] <input>
    zerolang_graph_roundtrip  zero graph roundtrip --json [--target] <input>
    zerolang_edit         zero graph patch --json <input> --op '<operation>'...

Adaptation for a stateless RL tool env: where Roder's `input` is a workspace
file path, here it is the Zero source TEXT. Each call writes the source to a
fresh temp file and runs the identical `zero` argv. `zerolang_edit` returns the
rewritten source so the model can carry it forward. On zero 0.2.0 the checked
patch is applied via inline `--op` operations (the documented form) rather than
Roder's `--patch-text`; the operation fields are identical.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile

try:
    import zero_runner  # vendored alongside this module
except ImportError:  # pragma: no cover
    from . import zero_runner  # type: ignore

# Canonical ordering for assembling an `--op` operation string.
_OP_FIELDS = [
    "node", "field", "expect", "value", "kind", "parent", "edge", "order",
    "name", "type", "path", "line", "column", "from", "to", "target",
    "public", "mutable", "static", "fallible", "exportC",
]
_OP_KINDS = {"set", "rename", "insert", "insertEdge", "replace", "delete"}
_TIMEOUT = 30


def _run(argv: list[str], files: dict[str, str]) -> tuple[bool, str]:
    ws = zero_runner.materialize(files)
    try:
        proc = subprocess.run(
            [zero_runner.zero_bin(), *argv], cwd=ws,
            capture_output=True, text=True, timeout=_TIMEOUT,
        )
        out = proc.stdout if proc.returncode == 0 else (proc.stderr or proc.stdout)
        return proc.returncode == 0, out
    except subprocess.TimeoutExpired:
        return False, "zero command timed out"
    finally:
        shutil.rmtree(ws, ignore_errors=True)


def _compact_json(ok: bool, raw: str, keep: int = 4000) -> str:
    if not ok:
        return json.dumps({"ok": False, "error": raw.strip()[:keep]})
    try:
        return json.dumps(json.loads(raw), separators=(",", ":"))[:keep]
    except json.JSONDecodeError:
        return raw.strip()[:keep]


def _esc(value: str) -> str:
    return (
        value.replace("\\", "\\\\").replace('"', '\\"')
        .replace("\n", "\\n").replace("\t", "\\t")
    )


def _op_string(op: dict) -> str:
    kind = str(op.get("op", "")).strip()
    if kind not in _OP_KINDS:
        raise ValueError(f"unknown op {kind!r}; expected one of {sorted(_OP_KINDS)}")
    parts = [kind]
    for key in _OP_FIELDS:
        if key not in op or op[key] is None:
            continue
        v = op[key]
        if isinstance(v, bool):
            parts.append(f"{key}={'true' if v else 'false'}")
        elif isinstance(v, int):
            parts.append(f"{key}={v}")
        else:
            parts.append(f'{key}="{_esc(str(v))}"')
    return " ".join(parts)


# --- the seven Roder-aligned tools ---

def zerolang_skills_get(skill: str = "zero", full: bool = False) -> str:
    """Read bundled Zero skill documentation such as language, graph, diagnostics, or agent."""
    argv = ["skills", "get", (skill or "zero").strip() or "zero"]
    if full:
        argv.append("--full")
    ok, out = _run(argv, {})
    return out.strip()[:6000] if ok else f"error: {out.strip()[:600]}"


def zerolang_check(source: str, target: str = "", emit: str = "") -> str:
    """Run `zero check --json` on the given Zero source and return diagnostics (JSON)."""
    argv = ["check", "--json"]
    if target.strip():
        argv += ["--target", target.strip()]
    if emit.strip():
        argv += ["--emit", emit.strip()]
    argv.append("main.0")
    ok, out = _run(argv, {"main.0": source})
    return _compact_json(ok, out)


def zerolang_graph_dump(source: str, target: str = "") -> str:
    """Run `zero graph dump --json`: the ProgramGraph with graphHash and node ids/values for patching."""
    argv = ["graph", "dump", "--json"]
    if target.strip():
        argv += ["--target", target.strip()]
    argv.append("main.0")
    ok, out = _run(argv, {"main.0": source})
    if not ok:
        return json.dumps({"ok": False, "error": out.strip()[:600]})
    try:
        d = json.loads(out)
    except json.JSONDecodeError:
        return out.strip()[:4000]
    # Compact node view (id/kind/name/type/value/line) to bound tokens.
    nodes = [
        {k: n.get(k) for k in ("id", "kind", "name", "type", "value", "line") if n.get(k) not in (None, "")}
        for n in d.get("nodes", [])
    ]
    return json.dumps({
        "graphHash": d.get("graphHash"),
        "moduleIdentity": d.get("moduleIdentity"),
        "counts": d.get("counts"),
        "validation": d.get("validation", {}).get("state"),
        "nodes": nodes,
    }, separators=(",", ":"))[:6000]


def zerolang_graph_view(source: str, target: str = "") -> str:
    """Run `zero graph view --json` to render canonical Zero source from source or a ProgramGraph."""
    argv = ["graph", "view", "--json"]
    if target.strip():
        argv += ["--target", target.strip()]
    argv.append("main.0")
    ok, out = _run(argv, {"main.0": source})
    return _compact_json(ok, out)


def zerolang_fix_plan(source: str, target: str = "") -> str:
    """Run `zero fix --plan --json` and return Zero's typed repair plan (JSON)."""
    argv = ["fix", "--plan", "--json"]
    if target.strip():
        argv += ["--target", target.strip()]
    argv.append("main.0")
    ok, out = _run(argv, {"main.0": source})
    return _compact_json(ok, out)


def zerolang_graph_roundtrip(source: str, target: str = "") -> str:
    """Run `zero graph roundtrip --json` to verify graph/source semantic stability."""
    argv = ["graph", "roundtrip", "--json"]
    if target.strip():
        argv += ["--target", target.strip()]
    argv.append("main.0")
    ok, out = _run(argv, {"main.0": source})
    return _compact_json(ok, out)


def zerolang_edit(source: str, graphHash: str, operations: list, validate: bool = True) -> str:
    """Apply checked ProgramGraph edits to the source.

    Provide the current `graphHash` (from zerolang_graph_dump) and a list of
    operations, each an object with `op` in {set,rename,insert,insertEdge,
    replace,delete} plus fields like node/field/expect/value. Returns JSON with
    the rewritten `source`, original/patched graph hashes, and (when validate)
    `zero check` results. Edits are rejected if the graph or `expect`
    preconditions do not match.
    """
    if not operations:
        return json.dumps({"ok": False, "error": "operations must be non-empty"})
    try:
        op_args = []
        for op in operations:
            op_args += ["--op", _op_string(op)]
    except ValueError as exc:
        return json.dumps({"ok": False, "error": str(exc)})

    ws = zero_runner.materialize({"main.0": source})
    try:
        # Enforce the stale-graph precondition (true "checked" edit, like Roder /
        # `zero graph patch --expect-graph-hash`). Rejects edits against a graph
        # hash the agent did not actually inspect.
        argv = ["graph", "patch", "--json", "main.0", "--expect-graph-hash", graphHash, *op_args]
        try:
            proc = subprocess.run(
                [zero_runner.zero_bin(), *argv], cwd=ws,
                capture_output=True, text=True, timeout=_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return json.dumps({"ok": False, "error": "zero graph patch timed out"})
        if proc.returncode != 0:
            return json.dumps({"ok": False, "error": (proc.stderr or proc.stdout).strip()[:800]})

        patched = ""
        path = os.path.join(ws, "main.0")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                patched = fh.read()

        result = {"ok": True, "source": patched}
        try:
            pj = json.loads(proc.stdout)
            result["originalGraphHash"] = pj.get("originalGraphHash")
            result["patchedGraphHash"] = pj.get("patchedGraphHash")
            result["operationCount"] = pj.get("operationCount")
        except json.JSONDecodeError:
            pass
        if validate:
            chk = subprocess.run(
                [zero_runner.zero_bin(), "check", "--json", "main.0"], cwd=ws,
                capture_output=True, text=True, timeout=_TIMEOUT,
            )
            result["check_ok"] = chk.returncode == 0
            if chk.returncode != 0:
                result["check_error"] = (chk.stderr or chk.stdout).strip()[:600]
        return json.dumps(result, separators=(",", ":"))[:8000]
    finally:
        shutil.rmtree(ws, ignore_errors=True)


ZERO_CODER_TOOLS = [
    zerolang_skills_get,
    zerolang_check,
    zerolang_graph_dump,
    zerolang_graph_view,
    zerolang_fix_plan,
    zerolang_graph_roundtrip,
    zerolang_edit,
]
