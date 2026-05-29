"""Generate verified `zero_graph_edit` tasks (checked ProgramGraph edits).

This is the graph-native family: the model must recover a target program from a
start program using CHECKED graph edits — `zero graph dump` to read node ids +
graphHash, then `zero graph patch --expect-graph-hash <h> --op 'set node="#.."
field="value" expect="OLD" value="NEW"'` — NOT by rewriting `.0` text.

Tasks are built by back-translation: take a canonical fixture, dump its graph,
pick a patchable literal node, and define a goal that changes that node's value.
The target source is produced by actually applying the gold `--op`, so every
task has a provably-reachable, compiler-validated answer. Tasks that don't
round-trip cleanly are dropped.

Graded by the `zero_graph_edit` rubric in the verifiers env (tools harness),
which rewards the graph-patch action, not text output.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import gen_zero_native as native

ZERO_VERSION = common.zero_runner.zero_version()
TIMEOUT = 30


def _zero(argv: list[str], files: dict[str, str]) -> tuple[bool, str]:
    ws = common.zero_runner.materialize(files)
    try:
        p = subprocess.run([common.zero_runner.zero_bin(), *argv], cwd=ws,
                           capture_output=True, text=True, timeout=TIMEOUT)
        return p.returncode == 0, (p.stdout if p.returncode == 0 else (p.stderr or p.stdout))
    except subprocess.TimeoutExpired:
        return False, "timeout"
    finally:
        shutil.rmtree(ws, ignore_errors=True)


def graph_dump(source: str) -> dict | None:
    ok, out = _zero(["graph", "dump", "--json", "main.0"], {"main.0": source})
    if not ok:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


def _esc(v: str) -> str:
    return v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")


def apply_set(source: str, ghash: str, node: str, expect: str, value: str) -> tuple[bool, str, bool]:
    """Apply one checked set op; return (patch_ok, new_source, target_compiles)."""
    op = f'set node="{node}" field="value" expect="{_esc(expect)}" value="{_esc(value)}"'
    ws = common.zero_runner.materialize({"main.0": source})
    try:
        p = subprocess.run(
            [common.zero_runner.zero_bin(), "graph", "patch", "--json", "main.0",
             "--expect-graph-hash", ghash, "--op", op],
            cwd=ws, capture_output=True, text=True, timeout=TIMEOUT,
        )
        if p.returncode != 0:
            return False, "", False
        with open(os.path.join(ws, "main.0"), encoding="utf-8") as fh:
            new_source = fh.read()
    except subprocess.TimeoutExpired:
        return False, "", False
    finally:
        shutil.rmtree(ws, ignore_errors=True)
    ok_chk, _ = _zero(["check", "--json", "main.0"], {"main.0": new_source})
    return True, new_source, ok_chk


def mutate_string(v: str) -> str:
    core, nl = (v[:-1], "\n") if v.endswith("\n") else (v, "")
    if not core:
        return "edited" + nl
    # deterministic, clearly-different, still a valid string literal
    if " " in core:
        return core.split(" ")[0] + " patched" + nl
    return core + "-patched" + nl


def mutate_int(v: str) -> str:
    try:
        return str(int(v) + 1)
    except ValueError:
        return v


UPSTREAM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upstream")


def specs():
    """(slug, title, source, provenance) from synthetic fixtures + official
    zerolang examples. The upstream examples are richer (types, enums, choices,
    match, generics, owned) and only need to `zero check` — graph edits don't
    require the program to run."""
    for slug, title, diff, tags, prompt, src, extra in native.specs():
        yield slug, title, src, {
            "source": "generated", "source_path": "tools/generators/gen_zero_native.py",
        }
    if os.path.isdir(UPSTREAM):
        for fn in sorted(os.listdir(UPSTREAM)):
            if not fn.endswith(".0"):
                continue
            name = fn[:-2]
            with open(os.path.join(UPSTREAM, fn), encoding="utf-8") as fh:
                src = fh.read()
            yield f"ex-{name}", f"example {name}", src, {
                "source": "zerolang", "source_path": f"examples/{fn}",
            }


def main():
    rows = []
    failures = 0
    seen_ids: set[str] = set()
    for slug, title, src, prov in specs():
        dump = graph_dump(src)
        if not dump:
            continue
        ghash = dump.get("graphHash")
        all_lits = [n for n in dump.get("nodes", [])
                    if n.get("kind") == "Literal" and str(n.get("value", "")) != ""]
        # Only edit literals whose value is UNIQUE in the program, so the goal
        # ("change the literal whose value is X") identifies exactly one node and
        # a correct checked patch reaches the gold target. Ambiguous values
        # (e.g. 0/1 appearing many times) make the task unsolvable-as-graded.
        from collections import Counter
        val_counts = Counter(str(n.get("value")) for n in all_lits)
        literals = [n for n in all_lits if val_counts[str(n.get("value"))] == 1]
        made = 0
        for n in literals:
            if made >= 2:
                break
            node_id = n.get("id")
            v = str(n.get("value"))
            ltype = str(n.get("type", ""))
            is_string = ltype.lower().startswith("str") or ("\n" in v) or any(c.isalpha() or c == " " for c in v)
            new_v = mutate_string(v) if is_string else mutate_int(v)
            if new_v == v:
                continue
            patch_ok, target, compiles = apply_set(src, ghash, node_id, v, new_v)
            if not (patch_ok and compiles):
                failures += 1
                continue
            kind = "string-literal" if is_string else "int-literal"
            task_id = f"zero_graph_edit/{slug}-{node_id.lstrip('#')}"
            if task_id in seen_ids:
                continue
            seen_ids.add(task_id)
            disp_old = v.replace("\n", "\\n")
            disp_new = new_v.replace("\n", "\\n")
            row = {
                "id": task_id,
                "title": f"Graph edit: {title} ({kind})",
                "family": "zero_graph_edit",
                "split": "train",
                "difficulty": 3,
                "tags": ["zero", "graph-edit", "program-graph", kind],
                "prompt": (
                    "Edit this Zero program using CHECKED ProgramGraph edits, not by "
                    "rewriting source text.\n\n"
                    f"Goal: change the {kind} whose value is currently `{disp_old}` so its "
                    f"value becomes `{disp_new}`.\n\n"
                    "Initial source (`main.0`):\n```zero\n" + src + "```\n\n"
                    "Inspect the graph (graphHash + node id), then apply a checked "
                    "`set` patch with the graphHash and an `expect` precondition."
                ),
                "starter_files": {"main.0": src},
                "expected": {
                    "target_source": target,
                    "forbidden_patterns": [],
                },
                "graph_objective": {
                    "graph_hash": ghash, "node": node_id, "field": "value",
                    "expect": v, "value": new_v,
                },
                "grader": {
                    "type": "zero_graph_edit", "entry_file": "main.0", "timeout_sec": 60,
                    "reward_version": "v1", "hidden": False,
                },
                "environment": {"type": "local", "requires_network": False, "requires_gpu": False},
                "provenance": {
                    "source": prov["source"], "source_path": prov["source_path"],
                    "license": "MIT", "zero_version": ZERO_VERSION,
                },
                "_fixture": {"target_source": target},
            }
            row["provenance"]["content_hash"] = common.content_hash(
                {k: row[k] for k in ("id", "prompt", "graph_objective", "_fixture")}
            )
            rows.append(row)
            made += 1

    common.stratified_splits(rows)
    counts = common.split_and_write(rows, "zero_graph_edit", "graph_edit")
    print(f"zero_graph_edit: {len(rows)} verified tasks, {failures} non-roundtrip skipped; splits={counts}")
    return rows


if __name__ == "__main__":
    main()
