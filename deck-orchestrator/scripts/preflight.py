#!/usr/bin/env python3
"""
Stage -1 preflight for the deck-orchestrator pipeline (the old tool-confirmation
skill, folded in). Proves the environment before any stage runs - a missing
binary discovered at stage 10 wastes the whole run.

Severities:
  BLOCK  - pipeline must not start; report the fix, never substitute tooling
  WARN   - a specific path degrades (visual QA render, schema check); log and go
  MANUAL - attested by the running agent, not tested here

Usage:
    python preflight.py [--brand aurecon]

Exit 0 = all BLOCK checks pass; 1 = at least one blocking failure.
"""

from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent.parent

BLOCK, WARN, MANUAL = "BLOCK", "WARN", "MANUAL"
results = []


def check(severity, name, ok, detail=""):
    results.append((severity, name, bool(ok), detail))


def resolve_node_module(module_name: str, node: str | None) -> tuple[bool, str]:
    if not node:
        return False, "not checked - node is missing"
    try:
        probe = subprocess.run(
            [node, "-e", f"console.log(require.resolve({module_name!r}))"],
            capture_output=True,
            text=True,
            cwd=REPO,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return False, f"timed out resolving {module_name}"
    if probe.returncode == 0:
        return True, probe.stdout.strip() or "resolvable"
    detail = (probe.stderr or probe.stdout).strip() or f"{module_name} is not resolvable"
    lines = [line.strip() for line in detail.splitlines() if line.strip()]
    for line in lines:
        if "Cannot find module" in line or line.startswith("Error:"):
            return False, line
    return False, lines[0] if lines else detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", default=None, help="brand pack the run will use")
    args = ap.parse_args()

    # 1. Binaries. Node runs the persisted pptxgenjs build script; python runs
    # the check scripts. LibreOffice/pdftoppm only degrade Fiona's render path.
    check(BLOCK, "binary: python", True, sys.executable)
    node = shutil.which("node")
    check(BLOCK, "binary: node", node,
          node or "missing - needed to run the pptxgenjs build script")
    pptxgenjs_ok, pptxgenjs_detail = resolve_node_module("pptxgenjs", node)
    check(BLOCK, "node module: pptxgenjs", pptxgenjs_ok, pptxgenjs_detail)
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    check(WARN, "binary: soffice (LibreOffice)", soffice,
          soffice or "missing - Fiona's ground-truth render degrades; "
                     "use the pptx skill's soffice wrapper if the harness has it")
    check(WARN, "binary: pdftoppm (poppler)", shutil.which("pdftoppm"),
          shutil.which("pdftoppm") or "missing - PDF -> slide images degrades")

    # 2. Python packages
    try:
        import jsonschema  # noqa: F401
        check(WARN, "package: jsonschema", True, "installed")
    except ImportError:
        check(WARN, "package: jsonschema", False,
              "missing - check_manifest.py skips the schema shape check")

    # 3. Skill files the pipeline sequences
    for skill in ["dylan-rules", "render-tufte-chart", "assess-graphical-excellence",
                  "brand-styler", "george"]:
        p = REPO / skill / "SKILL.md"
        check(BLOCK, f"skill: {skill}", p.is_file(), str(p))
    check(BLOCK, "schema: manifest.schema.json",
          (HERE.parent / "manifest.schema.json").is_file())

    # 4. Brand pack
    if args.brand:
        tokens = REPO / "brand-styler" / "brands" / args.brand / "tokens.json"
        ok = tokens.is_file()
        detail = str(tokens)
        if ok:
            try:
                json.loads(tokens.read_text())
            except ValueError as e:
                ok, detail = False, f"tokens.json invalid JSON: {e}"
        check(BLOCK, f"brand pack: {args.brand}", ok, detail)

    # 5. Manual attestations - the agent confirms these in the run log
    check(MANUAL, "harness: pptx skill available",
          None, "the maintained pptx skill (pptxgenjs guidance, validate.py, "
                "thumbnail.py, soffice wrapper) is loadable in this harness")
    check(MANUAL, "harness: can view rendered slide images", None,
          "needed for Fiona's visual QA; else accept degraded QA explicitly")
    check(MANUAL, "harness: can spawn subagents", None,
          "needed to run role stages in isolated context")

    blocked = False
    for sev, name, ok, detail in results:
        if sev == MANUAL:
            print(f"MANUAL  {name}: attest - {detail}")
            continue
        mark = "ok" if ok else "FAIL"
        print(f"{sev:5}  {mark:4}  {name}" + (f"  ({detail})" if detail else ""))
        if sev == BLOCK and not ok:
            blocked = True
    print("RESULT: " + ("BLOCKED" if blocked else "OK"))
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
