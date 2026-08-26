# PptxGenJS build tokens

How to turn the active pack's `tokens.json` into build constants and on-brand
helper snippets. Everything below is brand-generic: it reads the pack at the
top and never hardcodes a hex.

## Constant block

Load the pack once at the top of the generator script:

```js
const fs = require("fs");
const path = require("path");

// meta.brand is read from the manifest passed to this script.
// manifest is assumed to be parsed before this block runs, e.g.:
//   const manifest = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const brand = manifest.meta.brand;   // e.g. "aurecon"

// Pass the brand-styler root as an environment variable or CLI argument so
// the generator is not coupled to a specific directory layout.
// e.g. BRAND_STYLER_ROOT=/path/to/brand-styler/brands node build_deck.js manifest.json
const BRAND_STYLER_ROOT = process.env.BRAND_STYLER_ROOT
  || (() => { throw new Error("BRAND_STYLER_ROOT env var is required"); })();
const PACK_DIR = path.join(BRAND_STYLER_ROOT, brand);
const T = JSON.parse(fs.readFileSync(path.join(PACK_DIR, "tokens.json"), "utf8"));

const C = T.colors;               // C.accent, C.text, C.background, C.grey_2...
const FONT = T.fonts.body;
const FLOOR = T.type_floor_pt;    // minimum size anywhere on a slide
const [RULE, HAIR] = T.line_weights_pt;   // e.g. 0.5 and 0.25
const LOGO = path.join(PACK_DIR, T.logo);
const ACCENT_TEXT = T.accent_as_text.allowed ? C.accent : T.accent_as_text.substitute;
```

PptxGenJS gotcha: hexes are bare - `color: C.accent`, never `"#" + ...`.

## Canvas

```js
pptx.layout = "LAYOUT_WIDE";      // 13.333" x 7.5"
```

## Title block - no underline, whitespace does the work

```js
slide.addText(eyebrowText.toUpperCase(), {
  x: 0.55, y: 0.35, w: 12.2, h: 0.3,
  fontFace: FONT, fontSize: 12, bold: true, color: C.grey_2, charSpacing: 2,
});
slide.addText(actionTitle, {
  x: 0.55, y: 0.62, w: 12.2, h: 0.9,
  fontFace: FONT, fontSize: 28, bold: true, color: C.text,
});
```

## Hairline table

```js
slide.addTable(rows, {
  x: 0.55, y: 1.8, w: 12.2,
  fontFace: FONT, fontSize: 13, color: C.text,
  border: [
    { type: "solid", pt: RULE, color: C.grey_4 },  // top
    { type: "none" },                              // right
    { type: "solid", pt: RULE, color: C.grey_4 },  // bottom
    { type: "none" },                              // left
  ],
  fill: { color: C.background },                   // no banding, ever
});
// Header row cells: { text, options: { bold: true, color: C.text } }
```

## On-brand native chart

```js
slide.addChart(pptx.ChartType.bar, data, {
  x: 0.55, y: 1.8, w: 7.5, h: 4.5,
  chartColors: seriesColors,        // see series colour order below
  showLegend: false,                // direct end-labels instead
  showTitle: false,                 // the action title carries the message
  valGridLine: { style: "none" },   // or a single grey_4 hairline at majors
  catGridLine: { style: "none" },
  catAxisLabelColor: C.grey_3, valAxisLabelColor: C.grey_3,
  catAxisLabelFontFace: FONT, valAxisLabelFontFace: FONT,
  catAxisLabelFontSize: FLOOR, valAxisLabelFontSize: FLOOR,
  catAxisLineColor: C.grey_4, valAxisLineColor: C.grey_4,
  barGapWidthPct: 60,
});
```

Series colour order (the emphasis series carries the accent, everything else
recedes):

```js
const seriesColors = [C.accent, C.grey_2, C.grey_3, C.grey_4, ...C.tertiary];
// Reorder so the EMPHASIS series gets C.accent; non-emphasis series take the
// greys in order; tertiary only once the greys are exhausted.
```

## Footer

```js
slide.addText(deckLabel, { x: 0.55, y: 7.08, w: 6, h: 0.3,
  fontFace: FONT, fontSize: FLOOR, color: C.grey_3 });
slide.addText(String(slideNumber), { x: 12.35, y: 7.08, w: 0.45, h: 0.3,
  fontFace: FONT, fontSize: FLOOR, color: C.grey_3, align: "right" });
```

## Cover / closer (the sandwich)

```js
slide.background = { color: C.dark_surface };     // or C.dark_surface_deep
slide.addImage({ path: LOGO, x: 0.55, y: 0.5, w: 1.6, h: 0.53 });
// The accent word on a dark cover may use C.accent directly - it reads well
// on dark even when accent_as_text.allowed is false (confirm in brand.md).
```

## What never to emit

No `shadow` options, no gradients, no 3-D chart types, no `line` options at
weights outside `line_weights_pt`, no fills on table body cells, no fonts other
than `T.fonts`, no font size below `FLOOR`, no colour outside `tokens.json`.
