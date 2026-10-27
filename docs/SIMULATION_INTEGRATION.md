# PRISM Simulation Integration & Multi-Storefront Ingestion

## 1. Overview of Preserved Simulation Pages

PRISM includes four realistic e-commerce storefront simulations located in `simulation/`:

1. **Amazon India (`simulation/amazon.html`)**:
   - Dark theme navbar with gold accents, category menus, search bar.
   - Comprehensive product picker with 4 demo products (`Paralink Nord 3 Pro`, `Paralink Refrigerator`, `Paralink Smart Controller`, `Paralink Gaming Monitor`).
   - Detailed product view: buy box, Prime badging, EMI options, and customer reviews section.
   - Interactive review submission form: star rating, review text, email input, optional photo upload.

2. **Flipkart (`simulation/flipkart.html`)**:
   - Flipkart signature blue header, "Plus F-Assured" badges, discount banners.
   - Verified purchase indicators and platform-specific review layout.

3. **JioMart (`simulation/jiomart.html`)**:
   - JioMart green/blue branding, delivery address selector, grocery & electronics styling.

4. **Custom Brand Store (`simulation/brand.html`)**:
   - Direct-to-Consumer minimalist aesthetic, high-res photography, direct customer review widget.

All pages are zero-build static HTML files that run directly in any browser and use the shared engine in `simulation/simulation.js`.

---

## 2. Ingestion Architecture & Data Flow

When a user submits a review on any simulation page:

```
 User Submits Review Form on amazon.html / flipkart.html / etc.
                            │
                            ▼
           Local Optimistic DOM Insertion
           (Review appears immediately with "just now" timestamp)
                            │
                            ▼
           HTTP POST http://localhost:5000/api/reviews/ingest
           (or Render Gateway /v1/ingest/adapter/*)
                            │
                            ▼
           Backend Ingestion Gateway
           - Validates RawReview envelope
           - Computes idempotency_key
           - Enqueues pipeline task
                            │
                            ▼
           Live SSE Stream Broadcast
           - PRISM Dashboard receives review.stage event
           - Live review counters increment across all open windows
```

### Shared Simulation Engine (`simulation/simulation.js`)
- Loads ~400 seed reviews from `simulation/reviews-data.js` and distributes timestamps realistically (from 6 months ago to "just now").
- Dispatches user submissions via `fetch(API_ENDPOINT, { method: 'POST', body: ... })`.
- Updates the universal live counter: `"X reviews analyzed across 4 platforms"`.

---

## 3. Roadmap: Expansion to 6 Simulated Sites (`SITE_A` to `SITE_F`)

To fully exercise the new multi-lane adapter architecture outlined in `docs2/data_source.md`, the simulation suite will expand to 6 distinct API shapes:

| Site | Platform Mock | API Shape Simulated | Scale / Characteristics |
| :-- | :-- | :-- | :-- |
| **SITE_A** | Enterprise Marketplace | REST, Cursor-paginated JSON | 5 integer stars, order dates, verified purchase |
| **SITE_B** | Regional Electronics Store| REST, Page/Offset JSON | 5 stars with half-stars (0.5 native) |
| **SITE_C** | Direct Brand Store | Webhook push on submission | 5 integer stars, warehouse code, order ID |
| **SITE_D** | Tech Specialist Store | Polling with ETag/If-Modified | 10-point scale (normalizes to 0.5 step), photo attachments |
| **SITE_E** | Community Hardware Forum | Minimal REST payload | Thumbs Up / Thumbs Down ($4.5$ / $1.5$ derived) |
| **SITE_F** | Warehouse Inventory Feed | Scheduled CSV drop | Full ERP export with manufacturing & dispatch dates |

The current 4 simulation pages (`amazon.html`, `flipkart.html`, `jiomart.html`, `brand.html`) continue to serve as the immediate, interactive demo environments for live review submission during presentations and judge walkthroughs.
