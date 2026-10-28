# Facebook publishing

Target: https://www.facebook.com/profile.php?id=61587766500345

Discover connectors first; use one only if it can verify the target, attach the image, publish,
and return a verifiable permalink. Otherwise use the supported authenticated Chrome browser tool
and its actual returned documentation. Do not import legacy runtimes or invent methods.

## Identity

Match exact page ID, visible company/page name, active composer identity, and create-post action.
A URL alone does not prove the active author. Save observations and screenshot to
`evidence/facebook-preflight.json`. Do not assume the visible name from the Chinese skill title.

If already authenticated and the target page explicitly offers to switch to its own identity,
click once; if a confirmation dialog names the same destination, confirm once. Reopen the exact
URL and verify identity/permission. This is one two-step sequence. Stop if switching is still
requested, an account chooser appears, or credentials, MFA, CAPTCHA, checkpoint, permission, or
ambiguous identity blocks progress. Never substitute a personal profile or another page.

## Submit and verify

1. Revalidate artifacts, recheck history per [publication-history.md](publication-history.md), and recheck author/target.
2. Open the page composer, paste exact `facebook.txt`, attach `social-upload.jpg`.
3. Inspect the rendered preview for complete text, correct image and page author. Check the
   actual AI disclosure control and current platform requirements. Leave a genuinely optional
   AI label **off by default**. When disclosure is required, provide it truthfully and enable
   the required setting. Do not disable a mandatory disclosure or remove a platform-applied
   label. If the distinction cannot be established, stop and report it. Save the observed
   requirement, control state and reason in the preflight evidence, not a guessed default.
4. Run `update_manifest.py ... --channel facebook --status pending --submission-started --history HISTORY_JSON`.
   It must succeed before final submit. It records immutable batch hashes.
5. Click final publish once.
6. Find the post on the target timeline/published list; verify author ID, text, image, timestamp,
   and published state (not draft/scheduled). Save screenshot and canonical public permalink.
   Reopen the permalink. Record anonymous access separately from authenticated verification;
   never claim anonymous verification when Facebook requires login.
7. Save `evidence/facebook-published.json`; record `published --url URL --evidence JSON`.

If uncertain, record `uncertain` and inspect published posts, drafts, scheduled content,
notifications, and the correct date range. Reconcile an existing post into this run. A second
and final submission requires concrete evidence of absence in
`evidence/facebook-reconciliation.json`, passed as `--reconciliation JSON`. If absence cannot
be established, stop as uncertain. Never retry speculatively, downgrade a published status,
delete successful posts, or republish because reporting failed.

Facebook can apply its own labels even with the optional setting off. Metadata cleanup and
wording changes cannot guarantee otherwise. An automatic label is not publication failure and
does not justify deleting/reposting. Record an observed automatic label separately from the
creator's optional disclosure setting; never claim the post is unlabelled without verification.
