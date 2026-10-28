# Local run evidence schemas

The scraper creates `catalog.json`, `selection-ledger.json`, and
`candidates/NN-ID/manifest.json`. Use the returned candidate directory; artifact paths are
relative to it. Do not hand-edit submission history. All observations must be real, not defaults.
New batches also retain `publication-history.json` and `history_policy: 1`. The history ledger
records eligible counts and skipped published/reserved product IDs. See
[publication-history.md](publication-history.md) for the input evidence contract.

## keyword-plan.json

`core_keyword`: object with `phrase`, `source_field`, and `quote`.
`related_keywords`: two to four objects of the same shape.
`intent`: `product-selection`. `buyer_stage`: `evaluation`.

Each phrase is 2–8 words, verbatim within its quote after punctuation normalization; each quote
is an exact substring of the selected field in `product.json` → `source_fields`.
Hyphen-separated words count separately. Do not use raw JSON HTML as the quote: use the saved
text field. Keywords must not contain model codes or overlap by phrase containment.

## review.json

Required: `product_url`, `source_reviewed: true`, `product_link_verified: true`, `conflicts: []`,
`copy_reviewed: true`, `all_claims_supported: true`, and `claims` (at least four objects).
Each claim: `text` (exact substring of facebook.txt), `source_field`, `quote` (verbatim source).
Cover feature lines and all factual statements, including qualifications elsewhere in the copy.

For new batches, `editorial_review` contains nonempty `product_angle`, `specific_buyer_need`,
and `variation_notes`, plus `history_compared: true` and `compared_post_urls`: the most recent
five available published copies from the saved history, ordered newest first (deduplicate by
post identity). Use an empty list only when no published copy is available; state that limitation
in notes. This review improves phrasing without changing the four-emoji-line format.

`image_review`: `identity_preserved: true`, `text_accurate: true`,
`reviewed_files: ["social.webp", "social-upload.jpg"]`, and nonempty `notes` describing actual
inspection and any recovery attempts. Review model/series conflicts manually.

## evidence/facebook-preflight.json

`page_id: "61587766500345"`, exact target `page_url`, `active_identity_verified: true`,
`create_post_available: true`, `verified_at` (ISO timestamp with offset), `visible_page_name`,
and `screenshot` (relative existing file). Refresh on resume and immediately before submit.

`ai_disclosure`: `requirement` (`optional`, `required`, or `not_offered`), `enabled` (actual boolean
state of the creator disclosure control), and nonempty `notes` explaining the observed control
and applicable requirement. Optional defaults off; required must be on. `not_offered` means
the control is actually absent, not that requirements were ignored. Stop for ambiguity. Any
platform-applied automatic label is separate; record it in notes, never switch it off to pass.

## evidence/facebook-published.json

`page_id`, `post_url`, `author_verified: true`, `text_verified: true`, `image_verified: true`,
`published_state_verified: true`, `verified_at` (ISO with offset), `public_access`
(`anonymous_verified` or `login_required`), and existing `screenshot`.
Optional `published_at` (ISO with offset) must reflect observed publication time; otherwise the
verification time is used. Document redirect differences and evidence tying author to target ID.

## evidence/facebook-reconciliation.json

For the second/final submit: `page_id`, `absence_confirmed: true`,
`published_list_checked: true`, `drafts_and_scheduled_checked: true`, `checked_at` (ISO with offset),
existing `screenshot`, and `notes` explaining the evidence establishing no prior publication.

## evidence/google-sheet-reporting.json

`spreadsheet_id`, `sheet_title`, actual integer `sheet_id`, `row_number` (>=2), five exact
`headers`, five expected `values`, five actual `readback_values`, `matched_rows: 1`,
nonempty `checked_ranges`, `verified_at` (ISO with offset), and exact `sheet_url`.
Use frozen `reporting.google_sheet.expected_values` from the manifest. This JSON is evidence,
not a replacement for the connector read.

Use `--error` for failed/blocked/uncertain outcomes. Never save tokens, cookies, credentials,
or unrelated private account information in artifacts/screenshots.
