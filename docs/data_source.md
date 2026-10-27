# PRISM Data Sources and Ingestion

Scope: digital, product-based sources only (online stores, marketplaces, brand websites, Google Maps and Google services). No social media, no public-service sources. All ingestion is legally framed: official APIs and feeds, authorised-staff capture on own listings, first-party widget, files and email, licensed feeds.

## 1. Three lanes, one gateway

```
 API LANE      sim site adapters (6) ─┐
               real APIs (later)  ────┤
 CAPTURE LANE  widget ────────────────┼──► Ingest gateway ──► raw_reviews ──► pipeline
               extension ─────────────┤     (validate, normalise rating,
 FILE LANE     CSV / JSON upload ─────┤      idempotency key, provenance)
               email forward ─────────┘
```

All lanes produce the same **RawReview envelope**.

## 2. RawReview envelope

```json
{
  "tenant_id": "t_01",
  "source_id": "src_site_a",
  "channel": "site_a",
  "kind": "review | rating_only",
  "source_review_id": "A-883201",
  "product": { "sku": "HP-NORD3", "name": "Nord 3 Pro", "external_id": "B0XYZ" },
  "rating": { "value": 4.5, "scale": "5_half", "derived": false },
  "text": "Sound mast hai but box poora pichak gaya tha",
  "title": null,
  "reviewed_at": "2026-07-18T09:12:00+05:30",
  "author": { "id_hash": "sha256:...", "display": "R***", "account_age_days": 41 },
  "order": { "order_id_hash": "...", "purchase_date": "2026-07-09", "dispatch_date": "2026-07-10",
             "delivery_date": "2026-07-14", "warehouse": "W2", "seller": "SellerX", "verified_purchase": true },
  "batch_code": null,
  "media": [{ "type": "image", "url": "https://...", "transcript": null }],
  "contact": { "email": "...", "consent_followup": true },
  "provenance": { "lane": "api|widget|extension|file|email", "adapter": "site_a_v1", "captured_by": null, "raw_hash": "..." }
}
```

Required: `tenant_id`, `source_id`, `product` (sku or external id), `rating` (for `review` and `rating_only`), `reviewed_at`. Everything else optional; missing context only lowers batch-inference confidence.

Validation rules:
- `rating.value` in {0.5, 1.0, ..., 5.0} after adapter normalisation; otherwise dead-letter with reason.
- `kind=rating_only` has no text and is still scored by the trust cascade (burst, author reuse) because ratings move averages.
- Email is stored only with `consent_followup=true`; kept encrypted, hashed for lookups.

## 3. Rating normalisation table (per adapter config)

| Source scale | Mapping |
| :-- | :-- |
| 5 integer stars | as is |
| 5 with half stars | as is (native 0.5 precision) |
| 10-point | `round(x / 2 * 2) / 2` → nearest 0.5 |
| 100-point | `x / 20` then nearest 0.5 |
| Thumbs up/down | 4.5 / 1.5 with `derived=true` (lower rating weight in comparisons) |
| Sentiment label only | not accepted as a rating; kept as text only |

## 4. API lane: 6 placeholder simulated sites

The sites are placeholders (`SITE_A` to `SITE_F`); rename when decided. Each simulates a different real-world API shape so the adapter layer and rating normalisation are genuinely exercised. Each site is a small storefront for the same 4 demo products with its own review submission page and a mock review API.

| Placeholder | API shape | Rating scale | Extra context it exposes |
| :-- | :-- | :-- | :-- |
| SITE_A | REST, cursor-paginated JSON | 5 integer | verified purchase, order dates |
| SITE_B | REST, page/offset JSON | 5 with half stars | seller name, helpful votes |
| SITE_C | Webhook push on new review | 5 integer | order id, warehouse code |
| SITE_D | REST with ETag/If-Modified polling | 10-point | verified flag, photos |
| SITE_E | Thumbs up/down plus text | thumbs | minimal metadata (stress test for low context) |
| SITE_F | Scheduled CSV drop (file feed) | 5 integer | full export incl. dispatch dates |

Adapter interface (`prism_core.sources`):

```python
class ReviewSource(Protocol):
    id: str
    def pull(self, cursor: str | None) -> tuple[list[RawReview], str | None]: ...   # polling sources
    def handle_webhook(self, payload: bytes, headers: dict) -> list[RawReview]: ...  # push sources
    def health_probe(self) -> ProbeResult: ...
```

Real adapters implement the same interface later. Candidate real sources to verify (not yet confirmed, to be researched): Google Business Profile reviews API, Google Play Developer reviews API, review-platform APIs used by e-commerce stores (for example Shopify or WooCommerce review apps), brand CRM/support exports. Marketplace seller dashboards without an API are covered by the extension lane.

Seeding: `seeds/` contains a generator that produces the demo story across the 6 sites (see Section 9) and a replay tool that pushes events through the real adapters at controlled speed.

## 5. Capture lane: widget (for companies with no API)

**Purpose:** cleanest first-party signal for small companies that cannot expose an API.

- Embed: `<script src="https://<api>/widget.js" data-key="pk_..." data-product="HP-NORD3"></script>`
- Public key with an **origin allowlist** and rate limit.
- **Flow:** (1) star rating in 0.5 steps, sent immediately as `rating_only` if the user leaves (so ratings count even without text); (2) feature-level quick ratings for the product's taxonomy (battery, packaging, build...); (3) optional text; (4) optional batch code (typed, scanned from a QR on the pack, or pre-filled by URL parameter `?b=`); (5) optional email with an explicit consent checkbox.
- Sends to `POST /v1/ingest/widget` with `provenance.lane=widget`, `batch_code` set (B0, confidence 1.0).
- Stack: vanilla TypeScript, no framework, under about 30 KB, Shadow DOM for style isolation, language selector (the widget UI itself supports major Indian languages).

## 6. Capture lane: browser extension (for dashboards with no API)

**Purpose:** reviews behind a seller dashboard or vendor portal have no API; staff export stale CSVs at best. The extension captures reviews **with context**, which feeds batch inference.

- Chrome MV3, TypeScript. Content scripts driven by per-site **site profiles** (JSON of selectors and field mappings) so adding a site means adding a profile, not code.
- **Authorised staff only**, **own listings only**, **user-initiated** (a "Capture visible reviews" button; no background crawling), within platform terms. Domain allowlist per tenant; the extension refuses to run on non-allowlisted pages.
- Captured: review text, rating, date, SKU, order/dispatch dates, warehouse, verified-purchase, review photos (URLs), review id.
- Sends batches to `POST /v1/ingest/extension` with `provenance.captured_by=user_id`.
- **Overlay (two-way):** a side panel/badge on the page shows PRISM's verdict for visible reviews (`trust`, `issue cluster`, `batch`, `confidence`), looked up by `raw_hash`/review id. This makes the extension a workflow tool, not only a collector.
- Auth: user-scoped token from the dashboard; token stored in extension storage; revocable.

## 7. File lane

- **CSV/JSON upload** (`POST /v1/ingest/file`): upload in the dashboard, then a column mapping step (saved per source as a mapping profile). Rating scale chosen at mapping time. Rejected rows downloadable with reasons.
- **Email forward:** a tenant-specific inbound address; the email provider's inbound webhook posts the message; a parser extracts reviews from known formats (marketplace notification emails or forwarded CSV attachments). Unknown formats go to a "needs mapping" state. Kept simple: it reuses the CSV mapping profile.

## 8. Source health monitor

Per source, evaluated every 10 minutes by the `source_health` task:

| Signal | How |
| :-- | :-- |
| Freshness | time since last successful pull or last event |
| Volume anomaly | items in last 24h vs EWMA baseline for that source; z-score |
| Error rate | failed pulls/webhooks / total in last 24h |
| Lag | median (ingested_at - reviewed_at) |
| Schema drift | unknown or missing fields vs expected profile |
| Rating distribution shift | sudden change in rating histogram (possible scale change) |

Status: `healthy | degraded | down | silent` (silent = no data where volume is expected). Emits `source.health` events and alerts; the dashboard "Sources" page and the Render dashboard (task runs per source) show the same picture. A drop in volume from one source also warns that comparisons involving that channel may be biased.

## 9. Seeded demo data (summary)

Full dataset description lives with the eval harness (`seeds/`), but the ingestion side must support:
- About 1,500 reviews over 16 weeks across the 4 demo products and 6 sites, in English, Hindi, Hinglish, Tamil, Kannada, Bengali (plus a few others).
- Ground truth labels: bot clusters, duplicates, sarcastic and mixed reviews, rating-only entries, short reviews.
- One headline **batch defect story** (packaging, batch B-0716, three channels, flat average rating) with a later simulated returns series for lead-time scoring.
- One **systemic issue** (battery degradation across batches) and one **channel-specific issue** (a seller on one site).
- A **version change**: a modification (new packaging, v1 → v2) with a measurable improvement.
- A few serious complaints (overheating) and a source outage (SITE_E goes silent for a week).

## 10. Idempotency and duplicates across lanes
The same review may arrive via API and via the extension. The `raw_hash` of normalised (source, review id or text, author, date) is checked at the gateway and again by the trust cascade (G2/G3) so duplicates across lanes do not double count.
