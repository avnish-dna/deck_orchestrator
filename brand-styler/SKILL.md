---
name: brand-styler
description: Apply a company's house visual identity to any slide deck or presentation from a swappable brand pack - palette, typography, layout grid, and the minimal-decoration formatting rules that keep a deck on-brand and uncluttered. Use whenever building, restyling, theming, or formatting a deck, slides, or PowerPoint that must carry a specific company brand, or whenever the user wants "on-brand" slides, mentions a brand pack, or names a packaged brand - Aurecon is the first installed pack - even if they only ask for the colours or fonts. Also use to add a new company brand as a pack. This skill supplies the visual layer only; pair it with the deck-narrative and Tufte chart skills for storyline and chart internals.
---

# Brand Styler

The house-style layer. It owns one thing: how a deck should look for a given
company - palette, type, layout, and the formatting rules that keep it on-brand
and uncluttered. It does not own the narrative or the chart internals.

The skill is split in two:

- **This file** - the invariant design system. Every rule below is written
  against *token names* (`accent`, `text`, `grey_3`...), never hexes. These
  rules do not change between companies.
- **A brand pack** - `brands/<name>/` holding `tokens.json` (the hexes, fonts
  and weights), `logo.png`, and an optional `brand.md` for pack-specific
  quirks. Swapping company = swapping pack. Nothing else changes.

Where this sits in the stack:

| Concern | Skill |
|---|---|
| Storyline, slide order, action titles, one-message-per-slide | the deck-narrative skill |
| Whether a chart is good / what genre to use / chartjunk | the chart-assessment skill |
| Producing a clean, honest chart | the chart-render skill |
| **How the deck looks for this company's audience** | **this skill + the active pack** |

Apply this skill's rules on top of those. They decide what goes on the slide;
this decides how it is dressed.

## Resolving the pack

1. Take the brand name from the request or the manifest's `meta.brand` field.
2. Read `brands/<name>/tokens.json` - every token referenced below resolves
   from it. Read `brands/<name>/brand.md` for quirks the tokens can't express.
3. No pack named or found -> ask, or list `brands/` and confirm. Never invent
   hexes for a company.

Installed packs: **aurecon**.

### Adding a new company

Copy `brands/aurecon/` to `brands/<newco>/`, replace the hexes/fonts/logo,
rewrite `brand.md` for that brand's quirks, and add the pack name to the
"Installed packs" line and this skill's description trigger list. That is the
entire change - no rule below is edited.

---

## Palette (token roles)

Three tiers, used strictly in order. Primary and secondary carry almost every
deck. Tertiary is a release valve for data only. Colour is functional - it
marks the point, it does not decorate.

### Primary - the default deck

| Token | Role |
|---|---|
| `accent` | The accent. Marks, fills, ticks, the highlighted data series, shape accents, the accent word on a dark cover. Check `accent_as_text` in the pack before ever using it as type. |
| `text` | Primary text - titles and body on the light background. |
| `background` | Content-slide background. The default. |
| `dark_surface` / `dark_surface_deep` | Full-bleed cover and closing slides. |

### Secondary - the neutral scale, use freely

| Token | Role |
|---|---|
| `grey_2` | Secondary text, supporting copy. |
| `grey_3` | Muted labels, captions, footers, chart axis labels. |
| `grey_4` | Hairlines, table rules, thin dividers, subtle neutral fills. |

### Tertiary - graphs and infographics only

`tertiary[]`, in its listed order. Use **only** when a chart or infographic has
more categories than the primary and secondary palette can carry. Never for
slide furniture, text, or fills outside a data graphic.

**Order of use: primary first, then secondary, and reach for tertiary only once
those are exhausted.**

### Accent as text (accessibility)

The pack's `accent_as_text` block governs this. If `allowed` is false, the
accent is too light to read as type on the light background: accent-coloured
**text** must use `accent_as_text.substitute`, and only at the weight/size the
block allows. Everywhere else the accent stays a mark or a fill. On a dark
cover the raw accent usually reads well and is the correct choice there - the
pack's `brand.md` says if not.

- One accent moment per slide. If two things carry the accent, nothing does.
- Never substitute a near-miss colour for the accent (`banned_colors` lists
  known offenders).
- No cream or beige backgrounds. `background` or a dark surface token only.

---

## Typography

The pack's `fonts.body` throughout, **minimum `type_floor_pt`** anywhere on the
slide. Do not pair a second typeface.

| Element | Size | Weight | Colour token |
|---|---|---|---|
| Eyebrow / kicker (caps, charSpacing ~2) | 12pt | bold | `grey_2` |
| Slide title (action title) | 26-30pt | bold | `text` |
| Section header | 18-20pt | bold | `text` |
| Body / table text | 13-15pt | regular | `text` or `grey_2` |
| Large stat numeral | 40-60pt | bold | `text`; or `accent_as_text.substitute` if it must carry the accent |
| Caption / footer / page number | `type_floor_pt` | regular | `grey_3` |

---

## Layout

- **Canvas**: 13.333" x 7.5" widescreen (PptxGenJS `LAYOUT_WIDE`, or a custom
  layout of those exact dimensions).
- **Margins**: 0.5" minimum; 0.5-0.65" is the working range. Keep them identical
  on every slide so elements sit on a shared grid.
- **Lines**: every rule, border, divider and axis line is one of the pack's
  `line_weights_pt` - nothing else. The heavier for visible structure; the
  lighter for the quietest hairlines.
- **Footer**: a short deck label left, slide number right, `type_floor_pt`
  `grey_3`, in the same position on every slide. Cover and closer can omit it.
- **Sandwich (recommended)**: a `dark_surface` (or `dark_surface_deep`) cover
  and closer, `background` content slides between them.

---

## Formatting rules

These keep the deck minimal and on-brand. Build everything as **native
PptxGenJS objects** - charts, tables, shapes, lines. Never paste a screenshot
or exported image of a chart or table; a flattened picture cannot be edited,
ignores the theme, and blurs on zoom.

**Tables**
- `background` rows. No zebra striping, no filled row backgrounds.
- Horizontal hairlines only, `grey_4` at one of the pack's line weights. Drop
  vertical rules.
- Header row bold in `text`.
- Minimum `type_floor_pt` text.

**Charts**
- The series that matters: `accent`. Other series: the neutral scale, `grey_2`
  then `grey_3` then `grey_4`. Only once primary and secondary are exhausted,
  draw from `tertiary[]` - in its listed order.
- No gridlines, or a single faint `grey_4` hairline at major ticks only.
- No legend where a direct end-label works. No chart border. Thin line weights
  (`line_weights_pt` only).
- No 3-D, no shadows, no gradients - on data or any other object.

**Citations and bibliography**
- Citation markers are superscript `[n]` in `text` (body colour) - never the
  accent, never boxed. Inline at the point of use, never a per-slide
  "Source:" footer line.
- The bibliography is an appendix slide: a plain numbered list,
  `type_floor_pt` minimum, `text` on `background`, no banding, hairlines and
  margins as any other content slide.

**Decoration - what to never add**
- No accent line or underline beneath titles. Use whitespace instead.
- No decorative colour bars, sidebar stripes, or card-edge accent strips. To
  set a card apart, use a subtle `grey_4` fill - never a shadow, never an edge
  stripe.
- No drop shadows, bevels, glows, or 3-D on any object - no exceptions. A flat
  `grey_4` (or near-`background`) fill is the only way to lift a card off the
  page.

---

## Build tokens (PptxGenJS)

`references/pptxgenjs-tokens.md` shows how to turn the active pack's
`tokens.json` into a ready-to-paste PptxGenJS constant block plus helper
snippets - title block with no underline, hairline table options, on-brand
native chart options. Read it when generating the actual deck so the build
matches this spec exactly.

---

## Brand lint (machine-checkable)

For an automated QA pass over a rendered or built deck, these are the brand
rules that can be verified as concrete assertions - no judgement required.
Resolve every token from the active pack before checking. Each failure names
its check:

- **BL1 One accent moment** - at most one `accent`/`accent_as_text.substitute`
  element per content slide.
- **BL2 No off-brand accent** - no colour in the accent's hue family outside
  `accent`, `accent_as_text.substitute`, and any `tertiary[]` entry (charts
  only). Anything in `banned_colors` is an automatic fail.
- **BL3 Accent never small type on light** - `accent` appears only as
  mark/fill; accent-coloured text follows the pack's `accent_as_text` block
  exactly.
- **BL4 Line weights** - every rule, border, divider, and axis line is one of
  `line_weights_pt` exactly.
- **BL5 Type floor** - no text below `type_floor_pt`; `fonts.body` only.
- **BL6 No decoration** - zero shadows, bevels, glows, 3-D, gradients, title
  underlines, or edge stripes anywhere in the XML.
- **BL7 Tables** - no cell fills except header treatments; horizontal rules
  only, `grey_4`.
- **BL8 Backgrounds** - `background` content slides; covers/closers only in
  `dark_surface`/`dark_surface_deep`; nothing cream or beige.

A visual-QA agent should walk BL1-BL8 against the rendered slides and report
each violation with its code, slide, and object.

## What good looks like

A `background` deck in the pack's body font, anchored by `text` and `grey_4`
hairlines, with the accent appearing once per slide on the thing that matters -
and a dark cover and closer to frame it. Accent-coloured type only ever appears
per the pack's `accent_as_text` rule; tertiary colours only inside a chart that
needed them. No stripes, no shadows, no banded tables, no second font, no
off-brand accent, and every line at one of the pack's two weights.
