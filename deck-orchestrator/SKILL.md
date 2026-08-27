---
name: deck-orchestrator
description: Coordinate a complete, end-to-end deck build by running the deck skills as staged role-agents over one shared manifest. Use whenever someone wants the *whole* pipeline rather than a single stage - "build the whole deck from this analysis", "run the deck pipeline", "orchestrate the deck", "take this analysis and produce a finished on-brand deck" (any packaged brand - Aurecon or another brand pack), "stand up the deck build". Takes completed analysis in and drives it through storyline, charting, chart assessment, narrative reconciliation, source verification, branding and assembly, with one human sign-off gate and the rest autonomous. This is the coordinator that sequences dylan-rules, render-tufte-chart, assess-graphical-excellence and brand-styler with gates between them - not any one of those skills. Defer to each of those for its own domain; this skill owns coordination, the manifest, the gates, and the stage discipline.
---

# Deck Orchestrator

The top of the deck stack. Where `dylan-rules` governs the narrative, the Tufte
skills govern charts, and `brand-styler` governs brand, this skill runs all of
them as staged roles over one shared manifest - taking completed analysis in
and producing a verified, on-brand deck out.

This is a **playbook, not an engine**. The agent reading this file *is* the
orchestrator: it runs each stage (spawning a subagent per role where the
harness allows, so each role works in clean context with only its own skill),
edits the manifest one stage at a time, and runs the mechanical check scripts
as hard gates. Execution of the actual .pptx - generation, validation,
thumbnailing, rendering - is delegated to the maintained **`pptx` skill**;
this skill never re-implements it.

## The cast

| Role | Skill it runs | Owns (its rows in the manifest) |
|---|---|---|
| **Orchestrator** | this skill | `meta`, `decisions`, citation numbers, stage transitions, the gates |
| **Anna** | `dylan-rules` | structure, storyline, action titles, exhibit briefs, the emphasis call |
| **Ben** | `render-tufte-chart` | builds charts as native PptxGenJS objects, grey and minimal, brand-blind |
| **Cooper** | `assess-graphical-excellence` | genre pre-flight, then scores charts (`exhibits/*/cooper`, genre) |
| **Edward** | `dylan-rules` R-rules + the verification gate | the number ledger and reference registry (`figures/*/verification`, `sources/*`) |
| **Daniel** | `brand-styler` (+ the active brand pack) | brand and the whole visual layer |
| **Fiona** | visual QA (vision pass over rendered slides) | what the reader actually sees (`slides/*/visual_qa`, `exhibits/*/visual_defects`) |
| **George** | `george` | adversarial scrutiny (`scrutiny`). Purely advisory |
| **Human** | - | sign-off, decision resolutions, scrutiny resolutions |

Edward has no standalone skill - he enforces the **R - References** family in
`dylan-rules` plus the verification gate below. Build (the actual .pptx)
reads/writes via the `pptx` skill.

**Stage discipline replaces the old code-enforced ownership map**: run one
stage at a time, and in each stage edit only that role's rows (the "Owns"
column). When a role runs as a subagent, hand it a read-only manifest view and
apply its returned changes yourself - the orchestrating agent is the single
writer. This is a deliberate trade: patch-time enforcement was dropped with
the engine; `scripts/check_manifest.py` verifies the *state* after every
stage instead.

## Stage -1: preflight

Before anything else:

```
python scripts/preflight.py --brand <pack>
```

- **BLOCK failures stop the pipeline.** Report them to the human with the fix.
  Do not substitute alternative tooling (no PowerPoint COM, no
  python-pptx-as-builder, no matplotlib PNG charts). The sanctioned toolchain
  is PptxGenJS + the `pptx` skill scripts, full stop.
- **WARN failures degrade specific paths** (Fiona's render, the schema shape
  check) - note them in the run log and continue.
- **MANUAL items are attested, not tested** - confirm in the run log that the
  `pptx` skill is loadable, rendered slide images are viewable, and subagents
  can spawn; or explicitly accept degraded QA.

## The flow

Completed analysis in any form (messy deck, xlsx, notes) is the input,
alongside the source materials behind it. `meta.brand` names the brand pack.

```
0. Inputs           analysis + source_materials (in_hand gates verification)
1. Anna  ingest     pull findings/exhibits, map to the answer-first section pyramid,
                    write storyline (title + message + exhibit brief per slide),
                    set exhibit type and the emphasis series for charts
2. Cooper pre-flight pick the Tufte genre per chart from data shape; flag multi-render
2b. George challenge George red-teams the ghost deck (kill shots / exposed flanks /
                    backup gaps) while the storyline is still cheap to change; his
                    challenges batch into the sign-off so the human approves the
                    narrative AND sees its known weaknesses in one sitting
3. HUMAN GATE       the only stop. Approve storyline (P1) + make every judgment call -
                    chart-vs-table, multi-render picks, George's storyline challenges
                    (address or accept as risk). Decisions batch here.
   --- back half runs unattended ---
4. route by type    chart -> Ben+Cooper ; table/stat -> dylan+Daniel ; diagram -> build+Daniel
5. Ben  build       native PptxGenJS chart spec, genre locked, grey, Tufte-correct.
                    Ben designs TO the message: the slide's action title, message, and
                    emphasis travel into his brief - the asserted figure must be the most
                    prominent thing on the graphic. Ben proposes N candidates and
                    the rubric picks the best (selection + iteration, not iteration alone)
6. Cooper score     hybrid. `score_rubric.py` is the hard gate (encodable rules, real
                    arithmetic); Cooper's model pass scores the perceptual criteria the
                    rubric can't encode (understood simply, direct-label fit,
                    default-challenge, message prominence).
                    Final = min(mechanical, perceptual) - judgement can demand better,
                    never excuse worse. >=8 passes; below -> ranked fixes -> Ben rebuilds
                    WITH the fixes and slide context (directed, never blind; cap 5;
                    early-escalate the moment a rebuild fails to improve the score)
7. Anna reconcile   chart still proves the message? title numbers match computed values?
                    contradiction -> human
8. Edward verify    every figure traces to a verifiable source (the arithmetic half is
                    `check_manifest.py`'s figure check); relevance is the judgement half -
                    does the document actually support the claim? An irrelevant source
                    escalates like an unverifiable one
9. Daniel brand     the pack's accent on Anna's emphasis, everything else grey; audit all
                    visual layers against brand-styler BL1-BL8
10. Orchestrator    assemble via the pptx skill (see "Building the deck"), assign [n],
                    render bibliography, one ground-truth render
11. Fiona visual QA render every slide to an image (pptx skill render path) and inspect
                    the ARTEFACT, not the spec - clipped text, overlapping direct labels,
                    collisions, off-canvas elements, F1-F4 in the render, one accent
                    moment. Blocking defects reopen the exhibit (beats the freeze - a
                    chart that can't be read is broken, not cosmetic); rebuild loop
                    capped at 2 passes. Covers every exhibit type, closing the gap where
                    tables and diagrams skip Cooper
12. Anna audit      dylan-rules Audit mode turned on the pipeline's own output: L2
                    titles-only read, T1 per slide, Q1-Q3 deck-wide - the deck-emergent
                    checks no per-exhibit stage can own. Flags batch into the delivery
                    pack alongside open decisions
13. George scrutiny the assembled pass: attack the finished argument as a skeptical
                    client reading it standalone. Everything upstream verified the deck
                    is CORRECT; George asks whether the argument survives a hostile
                    room. Advisory only - challenges land in `scrutiny`, appear in the
                    delivery pack, and NEVER block. Only the human resolves them:
                    'addressed' or 'accepted_risk' - both legitimate, both recorded
```

After **every stage**, run the state gate:

```
python scripts/check_manifest.py <manifest.json>
```

and before assembly, the hard form:

```
python scripts/check_manifest.py <manifest.json> --gate assemble
```

A non-zero exit blocks the next stage until resolved.

## Routing by exhibit type

One flag Anna sets per exhibit. `chart` -> Ben + Cooper. `table` / `stat` /
`callout` -> built straight to the `dylan-rules` F-rules and `brand-styler`,
skips Cooper. `diagram` (rare) -> built from native shapes, Daniel brands,
skips Cooper. Ben and Cooper are chart-only; running Tufte criteria on a table
is a category error. **Every** exhibit type, Cooper-scored or not, passes
through Fiona's visual QA at the end - the render is inspected regardless of
route.

## The gates

- **One human gate** - storyline sign-off, at the front. Everything needing the
  human batches into `decisions`.
- **Cooper-Ben loop** - cap 5 rebuilds, pass threshold 8, and rebuilds are
  *directed*: Cooper's ranked fixes (mechanical + perceptual, B/C-tagged) go
  into Ben's rebuild brief. **Early exit** - a rebuild that fails to improve
  the score escalates immediately rather than burning the cap; a non-converging
  loop is information, not something to retry blindly. Freeze
  (`exhibits/*/cooper/frozen`) flips on at `branded`.
- **Freeze override** - a frozen chart reopens to `needs_rebuild` the moment
  Edward flags an integrity failure, Anna flags a contradiction, or Fiona logs
  a **blocking** visual defect. Cosmetic passes cannot break a freeze; factual
  and legibility failures always do - a chart that cannot be read is a broken
  chart, not a styling preference. Fiona's `minor` defects never break a
  freeze; they batch into the delivery pack.
- **George is not a gate** - by design. His challenges are the questions the
  client will ask in the room; the pipeline surfaces them, the human answers
  them. An open challenge never blocks assembly or delivery, George cannot
  write `resolution`, and `accepted_risk` is a first-class outcome - a
  judgement call recorded in the manifest rather than an oversight.
- **Relevance gate** - Edward's check is "legitimate + relevant", and relevance
  is judgement, not arithmetic: does the document actually support the claim,
  or merely mention the topic? An irrelevant source escalates exactly like an
  unverifiable one.
- **Verification gate** - nothing assembles while any source is not `verified`
  or any figure is not `verified`. **Unverifiable is a blocking defect, not a
  footnote** - a claim whose source cannot be inspected must be sourced or
  pulled. `check_manifest.py --gate assemble` is the mechanical form.
- **Escalation caps** - a figure mismatch/unanchored or an unverifiable source
  routes back to Anna as an open `decisions` row; at 2 rounds it becomes a
  `hard_stop` and the stage blocks until the human resolves it.

## The manifest

Single source of truth. Normalised, not nested: `slides`, `exhibits`,
`figures`, `sources` are flat collections cross-referenced by id, so each
role's stage patches only its own rows. Shape and enums are in
`manifest.schema.json`; cross-reference integrity, figure arithmetic and the
gates are checked by `scripts/check_manifest.py`. `meta.brand` names the
brand pack.

Two integrity structures Edward owns:
- **Number ledger** (`figures[]`) - `shown -> anchor -> transform -> source_value
  -> verification`. Provenance is captured upstream by Anna/Ben so Edward
  verifies a specific claim against a specific location, never re-derives.
  The arithmetic (shown vs source_value through the transform) is mechanical
  and lives in `check_manifest.py`.
- **Reference registry** (`sources[]`) - `claim -> source -> [n] -> bibliography
  entry -> verification + relevance`. The orchestrator assigns `[n]`
  deterministically (order of first appearance across slides, in slide order)
  and renders the bibliography appendix from this. Edward is its auditor.

## Inputs

At t=0 the orchestrator expects completed analysis plus the **source
materials** behind it. `inputs.source_materials[].in_hand` gates verification:
a source with the document attached can be checked for legitimacy and
relevance; a source that's only a citation can only be checked for
well-formedness and is flagged unverifiable. For real legitimacy checking,
hand over the documents, not just citations pointing at them.

## Building the deck (stage 10)

Assembly is delegated to the maintained **`pptx` skill** - read its SKILL.md
and follow it exactly. The contract:

1. **Gate first.** `check_manifest.py --gate assemble` must exit 0. Never
   build from an unverified manifest.
2. **Write a pptxgenjs generator script** for this deck, per the `pptx`
   skill's guidance and gotchas (layout before slides, bare hexes, native
   charts, validate after write). Style constants come from the brand pack via
   `brand-styler/references/pptxgenjs-tokens.md` - never hardcode a hex.
3. **Persist the generator** as `build_deck.js` next to the manifest. The
   deck must be regenerable with `node build_deck.js` - the script is a run
   artefact, not a throwaway.
4. **Validate**: run the `pptx` skill's `validate.py` on the output. Fix
   faults in the generator, never by hand-editing packed XML.
5. **Render** for Fiona: the `pptx` skill's render path (its `soffice`
   wrapper -> PDF -> images, or thumbnail grid). If no render path exists
   (preflight WARN), record degraded visual QA explicitly.

Everything on the slides is native PptxGenJS objects - charts, tables, shapes,
lines. No screenshots, no embedded chart images (F4).

## Boundaries

This skill owns coordination, the manifest, the gates, and the stage
discipline. It defers every domain to its skill - narrative and structure to
`dylan-rules`, chart internals to `render-tufte-chart` and
`assess-graphical-excellence`, brand to `brand-styler` (+ the active pack),
the .pptx itself to `pptx`. It never re-implements their rules; it runs them
in order and enforces what happens between them.

## Files

- `manifest.schema.json` - the manifest contract (JSON Schema 2020-12)
- `scripts/preflight.py` - stage -1 environment check (BLOCK/WARN/MANUAL)
- `scripts/check_manifest.py` - the mechanical state gate: schema, cross-refs,
  figure arithmetic, verification gate, escalation caps, brand pack
- `example_manifest.json` - a worked mid-pipeline manifest (stage `verify`,
  with an unverified source blocking assembly)
- `example_manifest_verified.json` - the same deck fully verified (stage
  `assemble`, passes `--gate assemble`)

Cooper's mechanical rubric lives with his skill:
`assess-graphical-excellence/scripts/score_rubric.py`.
