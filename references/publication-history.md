# Check publication history before selection

Use the publishing workspace's existing `campaign-runs` root, including every prior run. Create
it if this is genuinely the first run. Keep history checks under a timestamped `history-checks/`
directory outside the skill/repository. Do not store account history in the public repository.

## Read and reconcile

1. Load `google-drive:google-sheets`. Read the Sheet identified in [reporting.md](reporting.md):
   metadata, headers and **all populated A:E rows**, using bounded chunks. Save actual tool
   returns. A failed read is not an empty publication history.
2. `publication_history.py` scans local live manifests. A verified published Facebook post
   counts even when Sheet reporting is pending/failed. Any submission marker without a verified
   post reserves that product until reconciled; never assume it failed. Dry runs and unsubmitted
   drafts do not count as publications. Product IDs/official URLs determine identity, not titles.
3. Map every Qingneng Sheet permalink to a local post or inspect its Facebook author and body.
   For an unmatched product post, save the observed official product URL(s), full copy, and
   tool/screenshot evidence. Several products in one post all count as published. Resolve a
   verified company/event post without products as `non_product`; never guess this classification
   because a link cannot be opened. If identification remains uncertain, stop before selection.
   If manual/unreported target-page posts are encountered, reconcile them too (using saved
   platform evidence and `resolved_posts`); do not assume the Sheet is a complete platform export.
4. Build a history snapshot. The script checks coverage, target IDs, source evidence hashes and
   post mappings. It normalizes story/permalink/posts URLs with the same Facebook story ID;
   different opaque IDs require actual platform evidence, not an assumed alias.
5. Scrape the **whole** current catalog, exclude published/reserved IDs, then randomly shuffle
   only eligible products. Keep skipped IDs/reasons and candidate attempts in the ledger. Up to
   ten evidence rejections can try other unused products; never fall back to a published product.
   If all products are covered, report this and stop. A targeted URL also cannot silently repost.

## Sheet history evidence

Create `sheet-history.json` from actual observations, alongside the raw readback files:

```json
{
  "spreadsheet_id": "18iLpJ7bpDbJzxYtg0vsSOQxOR2e0KBuMI9C7LK0MhAw",
  "sheet_title": "工作表1",
  "headers": ["域名", "发布时间", "发布的站内链接", "Facebook链接", "LinkedIn链接"],
  "checked_at": "<actual ISO timestamp with offset>",
  "complete": true,
  "last_row": 1,
  "checked_ranges": ["工作表1!A1:E1"],
  "raw_readback_file": "sheet-readback.json",
  "rows": [],
  "resolved_posts": []
}
```

The empty rows/last_row=1 example is valid **only for a genuinely empty Sheet**. For a populated
Sheet, `rows` contains every row 2 through the observed `last_row`, each as
`{"row_number": N, "values": [A, B, C, D, E]}`; pad cells omitted by the connector with empty
strings, retaining blank rows. Do not drop other domains or rows between read chunks. Store
the actual complete raw responses in `raw_readback_file` (relative path).

Each unmatched post resolution has `post_url`, `author_verified: true`, `product_urls` (all
observed canonical product URLs), `copy` (full actual body), and `evidence_file` (relative
readback/screenshot path). For verified non-product content use `product_urls: []` and
`non_product: true`. The same structure can include encountered unreported Facebook posts.
Never fabricate a product URL from a model name. Keep raw observations and derived mappings
separate; the JSON validator cannot establish semantic truth or authenticate a screenshot.

```bash
python3 scripts/publication_history.py --runs-root WORKSPACE/campaign-runs \
  --sheet-evidence CHECK/sheet-history.json --output CHECK/history.json
python3 scripts/scrape_product.py --mode live --output-root WORKSPACE/campaign-runs \
  --history CHECK/history.json
```

History must be no older than two hours when selecting. Immediately before the first submit,
refresh the Sheet read/mappings and rebuild if needed; `update_manifest.py --history ...`
requires evidence within 30 minutes and rescans local runs under a short filesystem lock before
recording the submission reservation. Another run using the same product then stops. If refresh
fails, keep prepared assets and stop before submit. The script does not itself read Facebook or
Google; all live checks still require the authenticated tools.

The candidate's `publication-history.json` preserves the selection/editorial snapshot; the
fresh submission snapshot is stored separately in `evidence/submission-history.json` and frozen.
Old completed batches remain valid. An old unsubmitted batch must obtain fresh history before
its first submit. Explicit resumes after a submission still require platform reconciliation
and preserve the frozen content; reporting-only repair never runs selection or publishes again.
