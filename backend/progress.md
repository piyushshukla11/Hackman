# PRISM Backend — Build Progress

**How to use this file:**
- Read before every session to see what's done and what's next.
- Update checkboxes and the "Last session" block after every session.
- Keep notes short — just enough to not duplicate or break work.
- **Docs win** over any decision made here if there's a conflict.

---

## Last Session
_Replace this after every session._

```
[2026-10-27] Completed MVP 1 (Gateway, Adapters, Rating Normalisation, Postgres):
             1. Setup: pyproject.toml, Dockerfile (multilingual-e5-small bake), render.yaml Blueprint.
             2. Config & Lexicons: settings.py, thresholds.yaml, sentiment_lexicon.yaml (250+ Hinglish/vernacular words).
             3. Database: base.py (TenantMixin), 27 SQLAlchemy models, HNSW index on reviews.embedding,
                unique idempotency key, Alembic initial migration 0001_initial_schema.
             4. Repositories: BaseRepository with mandatory tenant_id enforcement across all 8 repo modules.
             5. Schemas: Pydantic v2 schemas across all layers, including Multimodal MediaItem and Onboarding.
             6. Auth & Catalog: deps.py, auth.py (onboarding + persona presets), catalog.py (custom features max 15).
             7. L1 Ingest & Adapters: accept() with SHA-256 idempotency, SITE_A-SITE_F sim-site adapters,
                ingest.py endpoints (adapter webhooks, public widget, extension batch, CSV/JSON file upload).
             8. Tests: test_mvp1_gateway_and_db.py passing all checks.
             Ready for MVP 2 (Trust Cascade G1-G6 & Language Normalisation).
```

---

## Stack (locked — do not change without updating docs)

| Layer | Choice |
|:--|:--|
| Language | Python 3.12 |
| API framework | FastAPI + Pydantic v2 |
| ORM / migrations | SQLAlchemy 2 (async) + Alembic |
| Database | Render Postgres + pgvector |
| Pipeline / workers | Render Workflows (Python tasks) |
| Embeddings | `intfloat/multilingual-e5-small` (384-d, ONNX int8, Docker-baked) |
| Translation | Sarvam Translate (formal, auto-detect source) |
| Sentiment | Full 7,500-word `vaderSentiment` + Indian e-commerce / Hinglish YAML lexicon + rating prior |
| LLM (ambiguity, surveys, OCR) | Gemini structured output |
| Email | `MailProvider` interface (Resend/Postmark style) |
| PDF | WeasyPrint (server-side) |
| Realtime | Postgres `LISTEN/NOTIFY` → SSE |
| Auth | HttpOnly JWT cookie (bcrypt, 8 h) |
| Runtime | Docker (Render web service + Workflows worker) |

---

## Repo layout (`prism-new/backend/`)

```
backend/
  prism_core/           # domain package — all business logic lives here
    config/
      thresholds.yaml   # all tunables; calibrated by scripts/calibrate.py
      settings.py       # pydantic-settings env config
    db/
      base.py           # SQLAlchemy declarative base + engine
      repositories/     # one repo helper per table group
    schemas/            # shared Pydantic models (RawReview, NormalisedReview, …)
    ingest/             # L1 — accept(), ReviewSource protocol, sources_health
    language/           # L2 — normalise()
    trust/              # L2 — score(), trust cascade G1-G6
    extract/            # L3 — analyse(), feature mapping, sarcasm gate
    serious/            # L3 — assess()
    batch/              # L3 — infer(), batch ladder B0-B4
    graph/              # L4 — rebuild(), edge weights, cluster classification
    trend/              # L4 — roll_up(), EWMA/CUSUM
    compare/            # L4 — run(), 5 lenses, statistics
    confidence/         # L4 — score(), formula + parts
    survey/             # L5 — plan(), send(), ingest_reply()
    mail/               # L5 — send(), templates, outbox
    report/             # L5 — build(), WeasyPrint PDF
    events/             # shared — emit(), pipeline_events + NOTIFY
    ml/                 # model wrappers (EmbeddingProvider, Translator, SentimentModel, LLMClient, ImageReader)
  api/                  # FastAPI app (routes only — no business logic)
    main.py
    deps.py             # shared dependencies (DB session, current user, tenant)
    routers/
      auth.py
      ingest.py
      catalog.py
      read.py
      actions.py
      ops.py
      stream.py         # SSE endpoint
      privacy.py
  workflows/            # Render Workflows task definitions (thin wrappers over prism_core)
    tasks/
      ingest_pull.py
      process_review.py
      rebuild_product.py
      survey_loop.py
      trend_scan.py
      weekly_digest.py
      source_health.py
      build_report.py
  alembic/              # migrations
  seeds/                # demo dataset generator + replay tool
  scripts/
    calibrate.py        # proposes threshold values from labelled seed data
    eval.py             # eval harness
  tests/                # pytest
  Dockerfile
  pyproject.toml
  render.yaml           # Render Blueprint
```

---

## MVP 1 — Gateway, Adapters, Rating Normalisation, Postgres

### Setup
- [x] `pyproject.toml` — deps: fastapi, uvicorn, pydantic-settings, sqlalchemy[asyncio], asyncpg, alembic, pgvector, python-jose, passlib[bcrypt], httpx, python-multipart, vaderSentiment, onnxruntime, sentencepiece
- [x] `Dockerfile` — Python 3.12, ML deps and `multilingual-e5-small` weights baked into image
- [x] `render.yaml` — Blueprint: web service (prism-api), Postgres (prism-db), Workflows worker (prism-workflows)
- [x] `prism_core/config/settings.py` — env vars: DATABASE_URL, SECRET_KEY, SARVAM_KEY, GEMINI_KEY, MAIL_PROVIDER_KEY, SLACK_WEBHOOK, RENDER_API_KEY
- [x] `prism_core/config/thresholds.yaml` — all initial values from contracts.md §9
- [x] `prism_core/config/lexicons/sentiment_lexicon.yaml` — 250+ curated Indian e-commerce & Hinglish sentiment words

### Database
- [x] `prism_core/db/base.py` — async engine, session factory, declarative base
- [x] SQLAlchemy models for all tables: `users`, `products`, `product_versions`, `modifications`, `batches`, `feature_taxonomies`, `sources`, `source_health`, `raw_reviews`, `reviews`, `review_features`, `trust_gate_log`, `graph_edges`, `issue_clusters`, `cluster_members`, `metric_rollups`, `trend_points`, `serious_complaints`, `surveys`, `survey_responses`, `email_outbox`, `alerts`, `reports`, `pipeline_events`, `eval_runs`, `returns_series`
- [x] All tables carry `tenant_id` and `created_at` ← test must fail if any query omits `tenant_id`
- [x] HNSW index on `reviews.embedding` (cosine)
- [x] Unique index on `raw_reviews.idempotency_key`
- [x] Alembic initial migration
- [x] `prism_core/db/repositories/` — one helper per table group, all enforce `tenant_id`

### Schemas (`prism_core/schemas/`)
- [x] `RawReview` — full envelope with all nested models (`ProductRef`, `RatingPayload`, `AuthorPayload`, `OrderPayload`, `MediaItem`, `ContactPayload`, `ProvenancePayload`)
- [x] `NormalisedReview`
- [x] `TrustVerdict`, `GateResult`
- [x] `ReviewAnalysis`, `FeatureMention`, `BatchInference`, `SeriousAssessment`
- [x] `Cluster`, `TrendPoint`, `Comparison`, `ConfidenceBreakdown`
- [x] `SourceHealth`, `ProbeResult`
- [x] All output classes: `IssueCard`, `SeriousComplaint`, `Investigation`, `TrendIndex`, `HealthIndex`

### Auth & Role Onboarding
- [x] `api/deps.py` — `get_db()`, `get_current_user()`, `require_role()`, `get_tenant_id()`
- [x] `api/routers/auth.py`:
  - POST `/auth/register`, `/auth/login`, `/auth/logout`, GET `/auth/me` (includes `role_title`, `selected_views`, `has_completed_onboarding`)
  - POST `/auth/onboarding` (first-login role title + selective module view checkboxes)
  - PATCH `/auth/me/preferences` (update workspace visible views or demo persona preset)
  - POST `/keys`
- [x] Bcrypt password hashing; HttpOnly JWT cookie; 8 h expiry
- [x] Seed script creates demo users (no hardcoded credentials in app code)
- [x] `api/routers/catalog.py`:
  - Products, Versions, Batches, Modifications CRUD
  - POST/GET `/v1/products/{id}/features` — Dynamic Company Custom Features (max 15 features; zero-shot `e5-small` embeddings + auto-anchor expansion)

### L1 Ingest — Gateway
- [x] `prism_core/schemas/raw_review.py` — `RawReview` envelope
- [x] `prism_core/ingest/__init__.py` — `accept(envelope: RawReview) -> RawID`
  - Validate schema
  - Rating normalisation per adapter config (table in contracts.md §2)
  - Compute `idempotency_key` (two formulas)
  - Write to `raw_reviews`; duplicate key → no-op
  - Enqueue `process_review` Render Workflow task
- [x] `prism_core/ingest/sources.py` — `ReviewSource` protocol
- [x] `prism_core/ingest/adapters/` — 6 sim-site adapters (SITE_A to SITE_F)
  - SITE_A: REST cursor-paginated JSON, 5 integer stars, verified purchase + order dates
  - SITE_B: REST page/offset JSON, 5 half-stars, seller name + helpful votes
  - SITE_C: Webhook push, 5 integer stars, order id + warehouse code
  - SITE_D: REST ETag/If-Modified polling, 10-point, verified + photos
  - SITE_E: Thumbs up/down + text (minimal metadata, stress test)
  - SITE_F: Scheduled CSV drop, 5 integer stars, full export with dispatch dates

### API — Ingest routes
- [x] `api/routers/ingest.py`
  - POST `/v1/ingest/adapter/{source_id}` — webhook push
  - POST `/v1/ingest/widget` — public key + origin allowlist + rate limit
  - POST `/v1/ingest/extension` — user-scoped token
  - POST `/v1/ingest/file` — CSV/JSON upload with column mapping profiles
  - POST `/v1/ingest/email` — inbound email parse webhook

### API — Catalog routes
- [x] `api/routers/catalog.py` — full CRUD for `/v1/products`, versions, modifications, batches, sources

---

## MVP 2 — Trust Cascade

### L2 Language
- [ ] `prism_core/ml/language_detector.py` — `LanguageDetector` (fastText-style + Unicode script ranges)
- [ ] `prism_core/ml/hinglish_detector.py` — `HinglishDetector` (Latin script + Indic function-word lexicon)
- [ ] `prism_core/ml/translator.py` — `Translator` interface; Sarvam (formal, auto-src) → LLM fallback → keep original + `lang_tier_penalty`
- [ ] PII masking applied before any external API call; mapping stays in-memory in task
- [ ] `prism_core/language/__init__.py` — `normalise(raw: RawReview) -> NormalisedReview`

### L2 Trust
- [ ] `prism_core/ml/embeddings.py` — `EmbeddingProvider`; multilingual-e5-small ONNX int8; `passage:` prefix for reviews, `query:` for anchors; batch encode 32-64; loaded once per worker
- [ ] `prism_core/trust/__init__.py` — `score(review) -> TrustVerdict`; all 6 gates in order; writes `trust_gate_log`
  - G1 Length: < 2 words → `rejected_short`; rating continues
  - G2 Exact dupe: hash of normalised text; same tenant/product
  - G3 Near-dupe: pgvector HNSW cosine search, threshold 0.95 (config); cross-language
  - G4 Content heuristics: promo patterns, links, phones, repeated emoji, generic one-liners
  - G5 Burst + coordination: z-score on product-channel-day counts; author reuse; template clustering; rating histogram shift
  - G6 Provenance: verified purchase, date plausibility, source reliability
- [ ] Trust score formula: start 1.0, subtract weighted gate penalties, add provenance bonus, clamp 0-1
- [ ] Rating effect: clean → `counted` (w=1.0); suspicious → `downweighted` (w=trust_score); bot rejected → `excluded`; short-only → `counted`

---

## MVP 3 — Understand (Feature Extraction + Ambiguity)

### L3 Extract
- [ ] `prism_core/ml/sentiment.py` — `SentimentModel` (Full 7,500-word `vaderSentiment` + augmented Indian e-commerce / Hinglish YAML dictionary; compact Transformer head); microsecond execution
- [ ] `prism_core/ml/ambiguity.py` — `AmbiguityScorer` first-pass (6 signals); result: `none/vague/mixed/sarcasm` + mult
- [ ] `prism_core/ml/llm_client.py` — `LLMClient` (Gemini structured output, JSON schema); fallback: rule-based + lower confidence
- [ ] `prism_core/extract/__init__.py` — `analyse(review, product_id) -> ReviewAnalysis`
  - Sentence split + embed (`multilingual-e5-small` with `passage:` prefix)
  - Feature mapping: zero-shot cosine to custom product features (max 15) and category anchors, relative margin (0.04) + floor, keyword lexicon merge, max 4 features/sentence
  - Polarity per feature: `vaderSentiment` + Hinglish lexicon + negation + rating prior `r' = (rating - 3) / 2`
  - Sarcasm/ambiguity gate (cheap signals first, LLM if above `t_high`)
  - Writes `review_features`

### L3 Serious
- [ ] `prism_core/serious/__init__.py` — `assess(review, analysis) -> SeriousAssessment`
  - Safety lexicon (multilingual) + semantic match to safety anchors
  - Score severity + urgency; insert `serious_complaints`; emit `serious.new`; optional Slack webhook
  - Suspicious reviews with safety keywords: surfaced but flagged unverified

### L3 Batch Inference
- [ ] `prism_core/batch/__init__.py` — `infer(review) -> BatchInference`; ladder B0-B4
- [ ] B1: OCR/vision via `ImageReader` (Gemini vision or Tesseract)
- [ ] B2: registry date+warehouse lookup (pure rules)
- [ ] B3/B4: cohort windows (labelled approximate in UI)
- [ ] Cold-start pooling with sibling batches, labelled `pooled`

### API — Read routes (partial — reviews + xray)
- [ ] `api/routers/read.py` — GET `/v1/reviews`, `/v1/reviews/{id}`, `/v1/reviews/{id}/xray`

---

## MVP 4 — Issue Graph + Batch Classification

### L4 Graph
- [ ] `prism_core/graph/__init__.py` — `rebuild(product_id) -> list[Cluster]`
  - Nodes = feature mentions; edges = same product + feature + polarity
  - Edge weight formula (4 components, threshold 0.45, top-k 8 — all from config)
  - Only trusted mentions (trust >= 0.40) enter; suspicious at reduced weight
  - Connected components → clusters
  - Classification: isolated / batch / systemic / channel_specific / praise
  - Calculate `defect_concentration` (% share in dominant batch, $p < 0.001$) and `lead_time_days`
  - Writes `graph_edges`, `issue_clusters`, `cluster_members`

### API — Issues routes
- [ ] GET `/v1/issues`, `/v1/issues/{id}` (with defect concentration, lead-time marker, and member verbatims)
- [ ] GET `/v1/issues/{id}/audit` — **Click-to-Verify Audit Drawer** (unedited raw reviews, verified purchase badge, trust gate audit log, source links)

---

## MVP 5 — Comparison Engine + Confidence + Health Score

### L4 Trend + Rollups
- [ ] `prism_core/trend/__init__.py` — `roll_up(product_id) -> list[TrendPoint]`
  - `metric_rollups` per (product, version, batch, channel, feature, week)
  - Trust-weighted rating sum + all-reviews sum (for with/without views)
  - Wilson interval on negative rate
  - EWMA/CUSUM change detection → `batch_spike`, `design_creep`
  - Spike alert if neg rate >= 0.60 + min sample, debounced 7 days

### L4 Compare
- [ ] `prism_core/compare/__init__.py` — `run(lens, a, b, metric) -> Comparison`
  - 5 lenses: product, time, batch, channel, version
  - Statistics: two-proportion z-test + Wilson CI; Mann-Whitney U + rank-biserial; Benjamini-Hochberg
  - Min n = 20 per side else `insufficient_data`
  - Version impact: target feature neg rate + rating before/after modification
  - Health score formula: `0.35 * rating_component + 0.45 * sentiment_component + 0.20 * (1 - open_issue_penalty)`

### L4 Confidence & Action
- [ ] `prism_core/confidence/__init__.py` — `score(cluster) -> ConfidenceBreakdown`
  - Formula with 5 terms + AmbiguityPenalty + CoherenceBonus + SurveyDelta
  - Store `confidence_parts` jsonb for waterfall UI
  - Levels: Act (>=0.75) / Monitor (0.45-0.74) / Gather (<0.45)
  - Severity: high (8+ mentions) / medium (4+) / low
  - Recommendation from (feature × issue_type) config matrix

### API — Full read routes & Ticket Export
- [ ] GET `/v1/overview`, `/v1/issues/{id}/confidence`, `/v1/serious`, `/v1/trends`, `/v1/compare`
- [ ] GET `/v1/issues/{id}/export` — **1-Click Ticket Exporter** (formats complete markdown/JSON bug ticket for Jira, Linear, or Slack webhook with root cause, verbatims, batch, and confidence waterfall)

---

## MVP 6 — Survey Loop + Email

### L5 Survey
- [ ] `prism_core/survey/__init__.py` — `plan()`, `send()`, `ingest_reply()`
  - Consent-only targeting (no email without `consent_followup=true`)
  - **RAG diagnostic question generator:** retrieves cluster verbatims + product spec sheet + batch/firmware details; structured Gemini prompt drafts 3 targeted root-cause diagnostic questions
  - Signed expiring token in survey link
  - Survey page: Jinja template served by FastAPI (no JS framework, mobile-first, language selector)
  - Reply ingestion: LLM 2-sentence summary; confirm/deny signal → SurveyDelta updates confidence
  - `survey_loop` Render Workflow: long-running, sleeps 7 days, reminder at day 3

### L5 Mail
- [ ] `prism_core/mail/__init__.py` — `send(template, to, ctx)`
  - `MailProvider` interface (Resend/Postmark-style)
  - Templates: `survey`, `serious_alert`, `digest_{qa,ops,support,marketing,leadership}`
  - Provider webhooks update `email_outbox.status`
  - Unsubscribe link in every survey email

### API — Action routes
- [ ] POST `/v1/investigations/{issue_id}/survey`, GET/POST `/v1/survey/{token}`
- [ ] POST `/v1/email/survey`, `/v1/email/digest`

---

## MVP 7 — Widget + Extension Ingest Handling

> Note: widget and extension code is frontend/browser work, but the **backend ingest endpoints and auth** for them belong here.

- [ ] Widget endpoint hardening: origin allowlist per tenant stored in `sources.config`, rate limit enforced
- [ ] Extension endpoint: `captured_by=user_id` provenance, batch capture (list of RawReview)
- [ ] Overlay lookup: GET by `raw_hash` / review id returning trust verdict + cluster + batch + confidence

---

## MVP 8 — Ops, Eval, Report, Judge Mode

### Source Health Monitor
- [ ] `prism_core/ingest/sources_health.py` — `evaluate(source_id) -> SourceHealth`
  - 6 signals: freshness, volume z-score, error rate, lag, schema drift, rating distribution shift
  - Emits `source.health` SSE events; writes `source_health` table

### Eval Harness
- [ ] `seeds/` — generator for ~1,500 reviews, 4 products, 6 sites, 16 weeks, 20+ languages, ground-truth labels
- [ ] `scripts/eval.py` — metrics: trust precision/recall, language F1, sarcasm F1, feature P/R, batch accuracy, detection lead-time, classification confusion matrix, confidence ECE
- [ ] `scripts/calibrate.py` — reads labelled seed data, proposes threshold values
- [ ] CI smoke test: small fixed subset, fails build if spam precision or batch recall drop below floors

### Company Report PDF
- [ ] `prism_core/report/__init__.py` — `build(product_id, range) -> bytes`
  - Sections: exec summary, health + trust note, product comparison, channel performance, batch/version impact, top issues with evidence, serious complaints, recommendations
  - HTML template (Jinja) → WeasyPrint PDF

### Realtime SSE
- [ ] `api/routers/stream.py` — GET `/v1/stream`
  - Postgres `LISTEN prism_events` connection
  - Fan-out to all connected SSE clients
  - Event kinds: `review.stage`, `trust.verdict`, `issue.updated`, `serious.new`, `survey.reply`, `source.health`

### Judge Mode / Demo
- [ ] POST `/v1/demo/replay` — pushes seeded dataset through real pipeline at controlled speed; returns SSE stream

### Ops routes
- [ ] GET `/v1/sources/health`, `/v1/pipeline/runs`, `/v1/eval/runs`
- [ ] POST `/v1/reports`, GET `/v1/reports/{id}/download`
- [ ] DELETE `/v1/privacy/author/{hash}` (DPDP compliance)

---

## Render Workflows tasks

| Task | Status |
|:--|:--|
| `process_review` (fan-out: normalise → trust → understand → batch_infer) | [ ] |
| `rebuild_product` (graph → rollups → compare_cache → score_issues) | [ ] |
| `notify` | [ ] |
| `survey_loop` (long-running, resume-safe) | [ ] |
| `trend_scan` (cron, hourly/daily) | [ ] |
| `weekly_digest` (cron, Mon 09:00 IST) | [ ] |
| `source_health` (cron, every 10 min) | [ ] |
| `build_report` (on-demand) | [ ] |
| `ingest_pull` (per-source cron + webhook) | [ ] |

---

## Cross-cutting requirements (always check these)

- [ ] Every query has `tenant_id` filter — test enforces this
- [ ] No mock data fallbacks anywhere — empty/error states are honest
- [ ] Every external AI call has a rule-based fallback; failures never silently dropped
- [ ] PII masked before any external call; mapping stays in-memory in the task
- [ ] `stage_versions` jsonb on `reviews` updated after every stage
- [ ] `events.emit()` called at start, done, failed, retry for every pipeline stage
- [ ] All thresholds read from `thresholds.yaml` — no magic numbers in code
- [ ] Idempotency: re-run with same version is no-op; version bump triggers reprocess

---

## Known differences from `prism-reference` (Node/SQLite) — do not port these patterns

| Reference | PRISM-new (correct) |
|:--|:--|
| Node.js / Express | Python 3.12 / FastAPI |
| SQLite + Sequelize | Postgres + pgvector + SQLAlchemy 2 async |
| Socket.io | SSE + Postgres LISTEN/NOTIFY |
| English-only MiniLM embeddings | multilingual-e5-small (384-d, ONNX int8) |
| Redis | none (rollups table replaces in-memory cache) |
| Hardcoded 7 features | per-category feature taxonomy in DB |
| Fixed count/week thresholds | baseline + significance tests |
| Mock data fallbacks | never — honest empty/error states |
| Hardcoded credentials | seed script only |
| Vercel deploy | Render Blueprint (`render.yaml`) |

---

## Render Accounts and Budget Tracking

**Total credits: $35 × 4 accounts = $140**

> **Demo-Safe Workaround:** Render Private Networking only works within a single account. To guarantee the live demo never breaks from public network lag, TLS drops, or egress timeouts, **all production services (`prism-db`, `prism-api`, `prism-workflows`, `prism-dashboard`) are co-located in Account 1 (PROD)** using native internal networking (`prism-db:5432`). Total prod cost is <$5 of Account 1's $35 credit. The other 3 accounts are used cleanly for Dev sandbox, Simulators, and a Hot Standby.

| Account | Label | Purpose | Services to provision | Credits budget |
|:--|:--|:--|:--|:--|
| Account 1 | **PROD (Live Demo)** | 100% stable live demo stack | `prism-db` (Postgres + pgvector), `prism-api` (FastAPI Docker), `prism-workflows` (worker), `prism-dashboard` (static) | ~$5 total (<$35) |
| Account 2 | **DEV / STAGING** | Development & test runs | Mirror of API & Workflows to test code without touching demo data | ~$10 max |
| Account 3 | **SIMULATORS** | E-commerce / feed simulators | Mock Play Store reviews, Shopify webhook generator | ~$10 max |
| Account 4 | **HOT STANDBY** | 1-click backup environment | Pre-configured dormant mirror of A1 ready if A1 ever experiences issues | $0 ($35 reserve) |

### Provisioning checklist (do before writing any code that calls Render APIs)

- [ ] Create Render account A1 (PROD); note team invite link
- [ ] Create Render account A2 (DEV / STAGING); note team invite link
- [ ] Create Render account A3 (SIMULATORS); keep for feeding mock data
- [ ] Create Render account A4 (HOT STANDBY); dormant backup clone
- [ ] Enable pgvector on A1 Postgres instance
- [x] **Demo safety implemented**: Co-locate API, DB, and Workflows on Account 1 so all communication uses Render Private Networking (sub-millisecond, never touches public internet)
- [ ] Create environment groups in Render: `prism-prod-secrets`, `prism-dev-secrets`
- [ ] Add all secrets to environment groups: DATABASE_URL, SECRET_KEY, SARVAM_KEY, GEMINI_KEY, MAIL_PROVIDER_KEY, SLACK_WEBHOOK
- [ ] Read Render Workflows SDK docs and confirm: fan-out API syntax, long-running sleep syntax, cron schedule syntax, task retry config
- [ ] Write `render.yaml` Blueprint and validate with Render CLI before committing

### Budget rules (enforce every session)
- Do not run embedding or LLM tasks on DEV account unnecessarily
- Seed replay (`POST /v1/demo/replay`) runs on PROD only, not DEV
- Workflows worker must scale to 0 between runs (no idle billing)
- Check Render dashboard spend before and after every demo dry-run
- If any account approaches $30 spent, stop and reassign to RESERVE

### Render Workflows SDK — things to confirm from docs before coding
- [ ] Exact import and decorator syntax for defining a task
- [ ] How to enqueue a task from the FastAPI app (HTTP call? SDK client?)
- [ ] Fan-out: how to launch N tasks in parallel and wait for all to finish
- [ ] Long-running: how to sleep a task and resume it on an external event
- [ ] Cron: how to define a scheduled task in `render.yaml`
- [ ] Retry config: how to set max attempts and backoff per task
- [ ] Subtasks: whether Render Workflows supports subtask chaining natively or if we chain via sequential awaits
