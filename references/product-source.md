# Official product evidence

Observed 2026-10-15; refresh contracts if the site changes. The English website renders product
data through Vue, so static HTML contains placeholders. Its public `js/common.js` declares
the backend used below. Use public GET endpoints only, never private/admin or submission APIs.

| Purpose | URL |
| --- | --- |
| Backend declaration | https://en.tsino-dynatron.com/js/common.js |
| Categories | https://enht.tsino-dynatron.com/api/product/category/list |
| Product catalog | https://enht.tsino-dynatron.com/api/product/list |
| Detail data example | https://enht.tsino-dynatron.com/api/product/info?productId=16 |
| Public detail example | https://en.tsino-dynatron.com/cp_xqy?pId=16 |
| Public catalog | https://en.tsino-dynatron.com/cp |

`16` is an example, not the default selection. The initial catalog had 20 products: servo drives,
servo motors, joint modules, controllers, and I/O. Do not hard-code the count. The list returns
`code: 0`, `total`, and `rows`; detail/category success also uses `code: 0`. Collect every page, deduplicate `productId`, reject repeated or
incomplete pages, and record coverage before shuffling. The candidate limit never limits catalog
pagination. `homeDisplay` is a homepage promotion flag, not eligibility; observed active status
is `"0"`. Stop if the contract changes rather than inventing new status meanings.

Use `productName`, `subhead`, `description`, `featuresAndBenefits`, `specifications`, and category
ancestry. Raw responses and separate text fields are retained. Several technical tables are
images: omit image-only specifications unless the exact value is corroborated in readable
product-specific text. Keep series ranges and conditions; never attribute every option to the
pictured variant. Do not transfer another model's claims to this product.

Official image hosts observed: `www.tsino-dynatron.com`, `tsino-dynatron.com`,
`en.tsino-dynatron.com`, and `enht.tsino-dynatron.com`. Source URLs can contain Chinese filenames
or HTTP links. Upgrade to HTTPS, percent-encode paths without double encoding, verify TLS, and
reject redirects outside these hosts.

Inspect hero and browser-rendered source. A fresh direct detail navigation was observed to
render blank because site code expects a cached dictionary. Visit the homepage first, then
navigate normally. Never inject storage or patch public site JavaScript. If a product link
remains broken, reject that candidate; if site-wide, stop the live run and report the problem.
Public source-extraction tests can still run locally.

Each selection job retains `catalog.json`, `selection-ledger.json`, and separate candidate
directories. Retry appends to the shared ledger, preserving rejected evidence. Limit to ten
untried candidates. Targeted products cannot be substituted. Network, TLS, schema, filesystem,
and tool failures stop the job; only product evidence/image problems reject a candidate.
Submission history in any candidate permanently forbids reselection.
