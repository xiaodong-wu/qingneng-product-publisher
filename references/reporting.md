# Google Sheet reporting

The user retained reporting with `不适用` in the disabled channel columns. Load
`google-drive:google-sheets` and use the authenticated connector.

- [social-auto-upload](https://docs.google.com/spreadsheets/d/18iLpJ7bpDbJzxYtg0vsSOQxOR2e0KBuMI9C7LK0MhAw/edit)
- Spreadsheet ID: `18iLpJ7bpDbJzxYtg0vsSOQxOR2e0KBuMI9C7LK0MhAw`
- Tab: `工作表1`; resolve current numeric sheet ID from metadata.
- Required headers: `域名`, `发布时间`, `发布的站内链接`, `Facebook链接`, `LinkedIn链接`.
- Row: `en.tsino-dynatron.com`, Shanghai `YYYY-MM-DD HH:mm:ss`, `不适用`, Facebook permalink, `不适用`.

Report only confirmed published Facebook posts. Use observed publication time, or verification
time when unavailable; freeze it in the manifest. Do not put a homepage/product/fake URL or an
empty value in disabled columns. Dry runs validate the prospective row locally without writing.

1. Read metadata and headers. Block if spreadsheet title, tab, or headers differ.
2. Search column D for the exact permalink across all populated rows using bounded chunks;
   record checked ranges. Do not inspect only recent rows.
3. Exactly one row matching all five values means already reported. Conflicting or duplicate
   permalink rows block reporting; never overwrite another campaign.
4. If absent, append one row. Read it back and verify all five strings and a unique match.
   If append outcome is ambiguous, search before any retry, never append speculatively.
5. Save `evidence/google-sheet-reporting.json`, record `reported`, and run completion validation.

Reporting failure never authorizes reposting or rollback. Report Facebook and Sheet states
separately. The local guard validates evidence consistency; it does not read the Sheet itself.
Never manufacture evidence from intended values without actual external reads.
