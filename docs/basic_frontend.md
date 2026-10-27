# PRISM Frontend (basic spec)

## 1. Rules

1. **Show the reasoning, not just the result.** Every visual must make visible something only PRISM can do. Plain line and pie charts are used only as supporting views.
2. **Every animation is driven by a real backend event** (SSE from `pipeline_events`). If nothing happens in the backend, nothing animates.
3. **No mock-data fallbacks.** Empty, loading and error states are honest and informative ("No reviews yet from SITE_C", "Pipeline failed at trust, attempt 3").
4. **One signature look.** The prism/forensic idea: white light in, split into coloured beams per feature. No generic card grids.
5. **Every number shows its support:** `n` reviews, how many quarantined, and a link to the reviews behind it.

## 2. Interfaces (different stacks, different audiences)

| Interface | Stack | Notes |
| :-- | :-- | :-- |
| Dashboard | React + Vite + TypeScript, Tailwind, shadcn/ui, TanStack Query, Zustand (SSE-fed store), d3 / visx for custom visuals, Framer Motion | main product UI |
| Survey page | Jinja templates served by FastAPI | no JS framework, mobile first, language selectable |
| Widget | Vanilla TypeScript, Shadow DOM | see `data_source.md` |
| Extension side panel | TypeScript + small UI (Preact allowed) | verdict overlay |
| Simulated sites | static/Node, 6 placeholders | their review forms post to the real ingest path |

## 3. Dashboard pages

| Route | Purpose | Main components |
| :-- | :-- | :-- |
| `/onboarding` | First-login role setup & module selection | Role title input (e.g. "Senior QA Lead"), module view checkboxes, persona preset chips |
| `/overview` | Portfolio health, top issues, serious queue count, source health strip | Health cards (trust-aware), Top issues, **Defect Concentration badge**, Alerts |
| `/stream` | **Prism Stream** (live pipeline view) | Stream canvas, stage lane, event log |
| `/issues` and `/issues/:id` | Issue cards and detail with evidence | Issue card, **Defect Concentration ($p < 0.001$)**, **Lead-Time Advantage marker**, **Click-to-Verify Audit Drawer**, **1-Click Ticket Exporter (Jira/Linear/Slack)**, **Confidence waterfall**, Evidence list, Batch/channel/language chips |
| `/reviews/:id` | **Review X-ray** | Highlight view, trust gates, translation diff, anchor similarities |
| `/timeline` | **Forensic lead-time timeline** | Channel lanes, batch capsules, rating line, detection marker, returns series |
| `/compare` | Comparison lenses | Lens switcher (product, time, batch, channel, version), result panel with CI and verdict |
| `/products/:id` | Product page: versions, modifications, batches, performance per site | Version timeline, Site performance matrix, **Custom Features Builder (max 15)** |
| `/serious` | Serious-complaint queue | Queue list, severity/urgency, status |
| `/investigations` | Closed loop surveys | **Survey thread** with confidence mover |
| `/sources` | Source health and ingestion | Health table, last sync, volume sparkline, upload and mapping |
| `/reports` | Company report PDF | Generate, list, download |
| `/settings` | Products, versions, batches, taxonomies, **Company Custom Features (max 15)**, API keys, widget snippet, users | Forms |
| `/judge` | Judge mode (guided 90s path) | Overlay stepper |

**Navigation & Personalization:**
- **First-Login Onboarding:** A new user types their title and selects their desired modules. Navigation selectively displays only their chosen views so the interface never feels crowded.
- **Top Bar Persona Quick-Switcher:** Judges and users can switch on-the-fly between curated personas:
  - *QA & Reliability Lead:* Prioritizes Issues, Forensic Timeline, Batch Ladder, Returns Series.
  - *Customer Experience Lead:* Prioritizes Prism Stream, Serious Complaints, Survey Loop, Customer Verbatims.
  - *Product Manager:* Prioritizes Custom Feature Trends, Comparison Lenses, Graph.
  - *Executive:* Prioritizes Portfolio Health, Financial Exposure, Health Index.
- Grouped by layer vocabulary (Ingest, Clean, Understand, Diagnose, Act) so the product explains itself.

## 4. Signature visuals (with required data)

### 4.1 Prism Stream (`/stream`)
- **What:** reviews flow in as white light. Spam is ejected with its reason code, Hinglish text morphs into its English translation, feature tags attach, then the stream splits into coloured beams, one per feature.
- **Data:** SSE events `review.stage` (stage, status, attempt), `trust.verdict` (reason), plus review snippet and translation from `GET /reviews/{id}`.
- **Honesty:** a retry in the Render task appears as a visible retry. A link opens the Render dashboard run.

### 4.2 Review X-ray (`/reviews/:id`)
- Highlighted words mapped to features; sarcasm/mixed marker with the signals that fired; original vs translated diff; similarity to each feature anchor; the list of trust gates with pass/warn/fail and reasons; rating shown beside text with the rating-text conflict indicator.
- **Data:** `GET /reviews/{id}/xray` returns analysis, gate log, anchor similarities, batch inference method and confidence.

### 4.3 Forensic lead-time timeline (`/timeline`)
- Complaint dots on **channel lanes**; a batch capsule snaps around a cluster when formed; below, the flat average rating line with the detection marker and the later returns spike; scrubber replays "PRISM flagged it on day 4, returns spiked on day 19".
- **Data:** `GET /trends?product=&granularity=day`, `GET /issues/{id}` (members with channel, date), returns series from the seed (`returns_series` table, labelled simulated).

### 4.4 Confidence waterfall
- Bars stacking Frequency, Density, Consistency, Temporal, Evidence, then the ambiguity penalty and coherence bonus and survey delta. Hover shows the reviews behind each bar.
- **Data:** `GET /issues/{id}/confidence` (the stored `confidence_parts`).

### 4.5 Batch flow map and language heatmap
- Warehouse → channel → region flow showing the affected path; India map coloured by language volume and issue density.
- **Data:** issue's `batches`, `channels`, review `warehouse`/region and `lang` aggregates.

### 4.6 Survey thread
- Conversation view per investigation; when a reply lands, the confidence number visibly moves (for example 0.62 → 0.81).
- **Data:** `GET /investigations/{id}`, SSE `survey.reply`.

### 4.7 Comparison view and site performance matrix
- Matrix of products × sites (health, rating, top negative feature) with trust-weighted values and `n`; lens results show deltas with confidence intervals and a plain-language verdict.
- **Data:** `GET /compare?lens=...`.

### 4.8 Trust panel
- Always available in the header: "412 reviews, 37 quarantined" with a toggle to view metrics with or without quarantined reviews.
- **Data:** `quarantined_n` in aggregate responses.

## 5. Role lenses

A top-bar switch re-arranges the same data (no separate permissions):
- **QA:** evidence, X-ray, batch details, confidence waterfall
- **Operations:** batch flow map, source health, channel comparison
- **Support:** serious queue, investigations, survey thread
- **Marketing:** feature praise clusters, site performance, version impact
- **Leadership:** one-line risk brief, health, lead-time headline, report download

## 6. Judge mode (`/judge`)

A 90-second guided path on the seeded dataset, running the **real** pipeline via `POST /demo/replay`:
1. Stream: reviews flow, spam ejected, Hinglish translated.
2. X-ray on one sarcastic review.
3. Timeline: cluster forms, batch capsule snaps, 4.4 line flat.
4. Waterfall: confidence 0.68.
5. Survey thread: replies, confidence to 0.84.
6. Compare: version lens shows the packaging change improved.
7. Render dashboard shown beside it (task runs, retries, fan-out).

Judge mode can be skipped; all pages work standalone.

## 7. State and data fetching
- TanStack Query for REST, Zustand store updated by one SSE connection (`/stream`) for live events, invalidating related queries.
- Skeleton loaders, never fabricated values. Errors show the request id and what failed.
- Accessibility basics: keyboard navigation, contrast in dark theme, reduced-motion respected (animations degrade to static states).

## 8. Out of scope (basic)
Custom alert-rule builders, white-labelling, multi-brand benchmarking, mobile app.
