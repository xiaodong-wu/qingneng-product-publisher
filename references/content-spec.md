# Facebook content and image contract

Audience: machinery builders, automation engineers, system integrators, industrial distributors,
and procurement teams. Brand spelling: TSINO DYNATRON. Category context explains the family but
cannot establish a particular model's capabilities.

## Copy

Write 80–150 English words excluding URL and hashtags, in this order:

1. Four emoji-led, product-evidenced feature lines.
2. A concise benefit paragraph tied to supported applications.
3. A direct B2B inquiry or evaluation call to action.
4. The full canonical product URL alone on a line.
5. Eight to twelve distinct relevant hashtags.

Keep this format; improve the writing within it. Start the four feature lines from this product's
most useful documented distinctions rather than reusing a stock four-sentence pattern. Pick a
concrete buyer need supported by the source (such as the documented interface, installation
arrangement, or commissioning function). Explain how those facts inform that buying decision;
do not invent customer pain points or quantified benefits. Prefer clear technical language to
empty adjectives. Avoid repeating filler such as "for your engineering team to evaluate" or
"compare against the requirements of your machine" after every feature.

Use the latest five available published texts in `publication-history.json` as a repetition
check. Vary feature emphasis, sentence construction, benefit reasoning and the CTA's requested
next step; preserve qualifications, exact model names and the fixed overall format. A CTA can
invite discussion of a documented configuration or application without promising unverified
services. Do not recycle a generic paragraph with only the model or URL replaced. Record
`editorial_review` in `review.json`, including why this angle suits the product and what changed
from recent copy. The validator blocks >=55% shared five-word sequences with a recent body
(URLs/hashtags excluded); passing that heuristic does not replace an actual editorial review.

Avoid unsupported guarantees, certifications, compatibility, performance rankings, ROI, prices,
MOQ, lead times, and OEM/ODM/private-label claims. Never generalize the catalog's EtherCAT,
voltage, axes, torque, encoders, or robot compatibility to one model. Include material operating
conditions. Do not repeat marketing superlatives as verified facts. Map all factual claims to
product text in `review.json`.

Create `keyword-plan.json`: one 2–8 word core phrase and two to four non-overlapping 2–8 word
related phrases, each with source field and verbatim quote. Remove whole model codes such as
CDA10, CDM-ANT, and JMDH, preserving meaningful terms such as EtherCAT, I/O, and servo. Keep
model codes in product names and copy. These keywords guide social copy; there is no long-form
article or keyword-density rule. General-context research cannot prove product specifications.

## One square four-panel image

Use the inspected official hero as the identity reference. Suggested panels: faithful hero,
supported detail, verified application, and integration context. Where an application lacks
evidence, use neutral studio compositions/alternate source crops. Keep model, housing, visible
ports, connectors, and module grouping materially accurate. Do not invent wiring, accessories,
safety labels, certification marks, or technical image text. Short supported English labels are
optional. Use a clean industrial style consistent with the live official site.

Inspect and record image review. Minor cosmetic differences are acceptable when identity and
buying decisions are unaffected. Allow two targeted corrections, then one source-preserving
fallback; stop for remaining material errors. Do not reselect to hide generator failure.

Retain `social.webp` plus temporary `social-upload.jpg`: 1:1, 960–1600 px per side, each ≤750 KiB,
no EXIF/XMP/ICC/comments. WebP quality floor 68; JPEG floor 72. Never upscale a small source.
Check readability after optimization. Upload the JPEG and retain the WebP as the canonical asset.

Metadata removal serves file optimization and privacy; it is not a way to promise avoidance of
AI detection or disclosure. Neither cleaned metadata nor rewritten copy guarantees Facebook
will not apply its own label. Follow the actual disclosure requirements in [publishing.md](publishing.md).

Machine validation checks structure and evidence consistency, not semantic truth or visual
accuracy. Source, copy, and image reviews must reflect actual inspection.
