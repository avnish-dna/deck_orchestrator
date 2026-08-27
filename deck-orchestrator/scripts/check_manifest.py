#!/usr/bin/env python3
"""
Mechanical state checks for a deck-orchestrator manifest.

Salvaged from the retired orchestrator.py engine. These are the deterministic
gates that must never run on a model:

  1. schema        - shape + enums (jsonschema, if installed)
  2. cross-refs    - every id reference resolves; citation numbers unique
  3. figures       - shown value matches source_value through the declared
                     transform (Edward's arithmetic)
  4. verification  - the assembly gate: every source and figure `verified`
  5. decisions     - open/hard_stop decisions; escalation-cap breaches
  6. brand pack    - meta.brand resolves to an installed brand-styler pack

Deliberately NOT here: patch-time ownership enforcement (the old OWNERSHIP
map). Stage discipline in the orchestrator playbook replaces it - agents run
one stage at a time and only their own rows are edited.

Usage:
    python check_manifest.py manifest.json              # all state checks
    python check_manifest.py manifest.json --gate assemble
        also fail (exit 1) if anything blocks assembly

Exit 0 = clean (for the requested gate); 1 = failures listed on stdout.
"""

from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
SCHEMA_PATH = HERE.parent / "manifest.schema.json"
BRANDS_DIR = HERE.parent.parent / "brand-styler" / "brands"

ID_FIELD = {
    "slides": "slide_id", "exhibits": "exhibit_id", "figures": "figure_id",
    "sources": "source_id", "decisions": "decision_id", "scrutiny": "challenge_id",
}
ANNA_ROUND_CAP = 2


# ---- 1. schema -------------------------------------------------------------
def schema_errors(m):
    if not SCHEMA_PATH.exists():
        return ["schema: manifest.schema.json not found next to this script"]
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return []  # soft-skip; report in main
    v = Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))
    return [f"schema: {'/'.join(map(str, e.path))}: {e.message}"
            for e in sorted(v.iter_errors(m), key=lambda e: list(e.path))]


# ---- 2. cross-reference integrity ------------------------------------------
def ref_errors(m):
    def ids(coll):
        return {it[ID_FIELD[coll]] for it in m.get(coll, [])}

    def dup_ids(coll):
        all_ids = [it[ID_FIELD[coll]] for it in m.get(coll, []) if ID_FIELD[coll] in it]
        return [i for i in set(all_ids) if all_ids.count(i) > 1]

    e = []
    sl, ex, sr = ids("slides"), ids("exhibits"), ids("sources")
    fi = ids("figures")
    sm_ids = {sm["source_material_id"] for sm in m.get("inputs", {}).get("source_materials", [])
              if "source_material_id" in sm}

    # Duplicate collection IDs
    for coll in ("slides", "exhibits", "figures", "sources", "decisions", "scrutiny"):
        for dup in dup_ids(coll):
            e.append(f"ref: duplicate {ID_FIELD[coll]} '{dup}' in {coll}")

    for s in m.get("slides", []):
        if s.get("exhibit_id") and s["exhibit_id"] not in ex:
            e.append(f"ref: slide {s['slide_id']} -> missing exhibit {s['exhibit_id']}")
        for c in s.get("citations", []):
            if c not in sr:
                e.append(f"ref: slide {s['slide_id']} cites missing source {c}")
    for x in m.get("exhibits", []):
        if x.get("slide_id") and x["slide_id"] not in sl:
            e.append(f"ref: exhibit {x['exhibit_id']} -> missing slide {x['slide_id']}")
        for fid in x.get("figure_ids") or []:
            if fid not in fi:
                e.append(f"ref: exhibit {x['exhibit_id']} -> missing figure {fid}")
        anchor = (x.get("data_ref") or {}).get("anchor") or {}
        smid = anchor.get("source_material_id")
        if smid and smid not in sm_ids:
            e.append(f"ref: exhibit {x['exhibit_id']} anchor -> missing source_material {smid}")
    for f in m.get("figures", []):
        if f.get("slide_id") and f["slide_id"] not in sl:
            e.append(f"ref: figure {f['figure_id']} -> missing slide {f['slide_id']}")
        if f.get("citation") and f["citation"] not in sr:
            e.append(f"ref: figure {f['figure_id']} cites missing source {f['citation']}")
        if f.get("exhibit_id") and f["exhibit_id"] not in ex:
            e.append(f"ref: figure {f['figure_id']} -> missing exhibit {f['exhibit_id']}")
        smid = (f.get("anchor") or {}).get("source_material_id")
        if smid and smid not in sm_ids:
            e.append(f"ref: figure {f['figure_id']} anchor -> missing source_material {smid}")
    for s in m.get("sources", []):
        if s.get("source_material_id") and s["source_material_id"] not in sm_ids:
            e.append(f"ref: source {s['source_id']} -> missing source_material {s['source_material_id']}")
        for sid in s.get("used_on") or []:
            if sid not in sl:
                e.append(f"ref: source {s['source_id']} used_on missing slide {sid}")
    nums = [s["citation"] for s in m.get("sources", []) if s.get("citation")]
    if len(nums) != len(set(nums)):
        e.append("ref: duplicate citation numbers in sources")
    return e


# ---- 3. figure arithmetic (Edward's mechanical half) -----------------------
# Supported transforms: applied to raw source_value before display comparison.
# Format: a dict mapping transform-keyword -> callable(raw) -> float
_TRANSFORMS = {
    "* 100":      lambda v: v * 100,
    "/ 1e6":      lambda v: v / 1e6,
    "* 1e-6":     lambda v: v / 1e6,
    "share":      lambda v: v * 100,   # share of count -> whole %
    "pct":        lambda v: v * 100,
    "%":          lambda v: v * 100,
}


def _apply_transform(raw, transform: str) -> float:
    """Execute the declared transform string against raw and return the result."""
    if not transform:
        return raw
    t = transform.lower()
    # Walk the registered keywords in order; apply the first match found.
    for kw, fn in _TRANSFORMS.items():
        if kw in t:
            return fn(raw)
    # No recognised keyword: return raw unchanged (the display compare will
    # catch the mismatch and report the error).
    return raw


def figure_matches(raw, transform, shown):
    """Apply the declared transform to the raw source value and compare to shown."""
    s = str(shown).strip()
    effective = _apply_transform(raw, transform or "")
    try:
        if s.endswith("%"):
            target = float(s[:-1])
            # After transform, effective must already be in % units.
            # If no transform keyword matched, effective == raw; the comparison
            # will correctly fail and surface the misconfigured row.
            return abs(round(effective) - target) <= 0.5
        if s.startswith("$") and s.lower().endswith("m"):
            target = float(s[1:-1])
            return abs(round(effective, 1) - target) <= 0.05
        target = float(re.sub(r"[^\d.\-]", "", s))
        return abs(effective - target) <= max(0.01, abs(target) * 0.01)
    except (ValueError, TypeError):
        return False


def figure_errors(m):
    e = []
    for f in m.get("figures", []):
        raw = f.get("source_value")
        if raw is None:
            continue  # not yet read from source; verification gate reports it
        if not figure_matches(raw, f.get("transform", ""), f.get("shown")):
            e.append(f"figure: {f['figure_id']} shown '{f.get('shown')}' does not match "
                     f"source_value {raw} via transform '{f.get('transform', '')}'")
        elif f.get("verification") == "verified":
            pass
        elif f.get("verification") in ("mismatch", "unanchored"):
            e.append(f"figure: {f['figure_id']} arithmetic passes but is marked "
                     f"'{f['verification']}' - re-run verification or fix the row")
    return e


# ---- 4. the verification gate (blocks assembly) ----------------------------
def assembly_blockers(m):
    b = []
    # 4a. Storyline sign-off: log must contain a 'storyline signed off' action.
    signed_off = any(
        "storyline signed off" in (entry.get("action") or "").lower()
        for entry in m.get("log", [])
    )
    if not signed_off:
        b.append("gate: storyline has not been signed off (no 'storyline signed off' log entry)")

    # 4b. Source verification + relevance (Edward's gate)
    for s in m.get("sources", []):
        if s.get("verification") != "verified":
            b.append(f"gate: source {s['source_id']} is {s.get('verification')} "
                     f"(claim: {s.get('claim', '')})")
        if s.get("relevance_ok") is not True:
            b.append(f"gate: source {s['source_id']} has not been judged relevant to its claim")

    # 4c. Figure verification
    for f in m.get("figures", []):
        if f.get("verification") != "verified":
            b.append(f"gate: figure {f['figure_id']} ({f.get('shown')}) is {f.get('verification')}")

    # 4d. Chart exhibits must have Cooper score >= pass mark and be frozen
    for x in m.get("exhibits", []):
        if x.get("type") != "chart":
            continue
        cooper = x.get("cooper") or {}
        score = cooper.get("score")
        frozen = cooper.get("frozen")
        if score is None:
            b.append(f"gate: exhibit {x['exhibit_id']} has no Cooper score - run score_rubric.py")
        elif score < 8.0:
            b.append(f"gate: exhibit {x['exhibit_id']} Cooper score {score} is below the 8.0 pass mark")
        if not frozen:
            b.append(f"gate: exhibit {x['exhibit_id']} Cooper chart is not frozen")

    # 4e. All slides (except template-managed sections) must be branded or frozen
    SLIDE_READY = {"branded", "frozen"}
    SLIDE_EXEMPT_SECTIONS = {"cover", "closer", "appendix"}
    for s in m.get("slides", []):
        if s.get("section") in SLIDE_EXEMPT_SECTIONS:
            continue
        if s.get("status") not in SLIDE_READY:
            b.append(f"gate: slide {s['slide_id']} status is '{s.get('status')}' "
                     f"(must be 'branded' or 'frozen' before assembly)")

    # 4f. All exhibits must be branded or frozen
    EXHIBIT_READY = {"branded", "frozen"}
    for x in m.get("exhibits", []):
        if x.get("status") not in EXHIBIT_READY:
            b.append(f"gate: exhibit {x['exhibit_id']} status is '{x.get('status')}' "
                     f"(must be 'branded' or 'frozen' before assembly)")

    return b


# ---- 5. decisions + escalation caps -----------------------------------------
def decision_errors(m):
    e = []
    for d in m.get("decisions", []):
        if d.get("status") == "hard_stop":
            e.append(f"decision: HARD STOP {d['decision_id']} ({d.get('object_ref')}): {d.get('prompt')}")
        elif d.get("status") == "open" and d.get("rounds", 0) >= ANNA_ROUND_CAP:
            e.append(f"decision: {d['decision_id']} at round cap ({d['rounds']}) - should be hard_stop")
    return e


# ---- 6. brand pack -----------------------------------------------------------
def brand_errors(m):
    brand = m.get("meta", {}).get("brand")
    if not brand:
        return ["brand: meta.brand is not set - name the brand pack to build with"]
    if not (BRANDS_DIR / brand / "tokens.json").is_file():
        installed = sorted(p.name for p in BRANDS_DIR.iterdir() if p.is_dir()) \
            if BRANDS_DIR.is_dir() else []
        return [f"brand: no pack '{brand}' in brand-styler/brands/ (installed: {installed})"]
    return []


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("manifest")
    ap.add_argument("--gate", choices=["assemble"], default=None,
                    help="also fail on assembly blockers")
    args = ap.parse_args()

    m = json.loads(Path(args.manifest).read_text())

    errors = []
    errors += schema_errors(m)
    errors += ref_errors(m)
    errors += figure_errors(m)
    errors += decision_errors(m)
    errors += brand_errors(m)

    blockers = assembly_blockers(m)
    open_dec = [d for d in m.get("decisions", []) if d.get("status") != "resolved"]
    open_scr = [c for c in m.get("scrutiny", []) if c.get("status") == "open"]

    try:
        import jsonschema  # noqa: F401
    except ImportError:
        print("note: jsonschema not installed - schema shape check skipped "
              "(pip install jsonschema)")

    print(f"stage: {m.get('meta', {}).get('stage')}    deck: {m.get('meta', {}).get('title', '')}")
    for x in errors:
        print(f"FAIL  {x}")
    print(f"assembly blockers: {len(blockers)}")
    for b in blockers:
        print(f"  - {b}")
    print(f"open decisions: {len(open_dec)}")
    for d in open_dec:
        print(f"  - [{d.get('status')}] {d.get('gate')} ({d.get('object_ref')}): {d.get('prompt')}")
    print(f"open scrutiny challenges (advisory - never block): {len(open_scr)}")
    for c in open_scr:
        print(f"  - [{c.get('severity')}] {c.get('target')}: {c.get('question')}")

    failed = bool(errors) or (args.gate == "assemble" and blockers)
    print("RESULT: " + ("FAIL" if failed else "OK"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
