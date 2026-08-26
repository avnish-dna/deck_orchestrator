#!/usr/bin/env python3
"""
Cooper's mechanical rubric - the hard gate of the hybrid chart score.

Encodable rules only, checked deterministically, never by a model. The
perceptual half (understood simply, direct-label fit, default-challenge,
message prominence) is a model pass run by the assessing agent; the final
score is min(mechanical, perceptual) - judgement can demand better, never
excuse worse.

Usage:
    python score_rubric.py manifest.json                # score every chart exhibit
    python score_rubric.py manifest.json ex_split       # score one exhibit
    python score_rubric.py manifest.json --pass-mark 8

Prints one JSON object per exhibit: {exhibit_id, score, fixes, pass}.
Exit 0 = every scored exhibit passes; 1 = at least one below the pass mark.
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

PASS_MARK = 8.0


def rubric(ex):
    """Pure mechanical rubric over one exhibit dict -> (score, fixes)."""
    series = (ex.get("data_ref") or {}).get("plotted_series") or []
    fixes, score = [], 10.0
    if ex.get("emphasis") in (None, "") and len(series) > 1:
        score -= 1.0
        fixes.append("B4: no series carries the so-what - set an emphasis")
    if len(series) > 6:
        score -= 2.0
        fixes.append("C3: too many series - switch to small multiples")
    if any(d.get("value") is None for d in series):
        score -= 3.0
        fixes.append("data: missing values in the plotted series")
    return max(0.0, min(10.0, score)), fixes


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("manifest")
    ap.add_argument("exhibit_id", nargs="?", default=None)
    ap.add_argument("--pass-mark", type=float, default=PASS_MARK)
    args = ap.parse_args()

    m = json.loads(Path(args.manifest).read_text())
    exhibits = [x for x in m.get("exhibits", []) if x.get("type") == "chart"]
    if args.exhibit_id:
        exhibits = [x for x in exhibits if x["exhibit_id"] == args.exhibit_id]
        if not exhibits:
            print(f"no chart exhibit '{args.exhibit_id}' in manifest", file=sys.stderr)
            return 2

    all_pass = True
    for ex in exhibits:
        score, fixes = rubric(ex)
        ok = score >= args.pass_mark
        all_pass &= ok
        print(json.dumps({"exhibit_id": ex["exhibit_id"], "score": round(score, 1),
                          "fixes": fixes, "pass": ok}))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
