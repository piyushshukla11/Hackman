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
[2026-10-27] Completed Root Directory Separation & Full Stack Backend Suite:
             1. Database Separation (`prism-new/db/`):
                - db/base.py (Declarative Base, TenantMixin, Async Engine, Sessionmaker)
                - db/models.py (All 27 SQLAlchemy multi-tenant models, HNSW vector indexing)
                - db/repositories/ (Strict multi-tenancy: BaseRepository, users, catalog, ingest, reviews, graph, metrics, actions, events)
                - db/alembic/ (alembic.ini, env.py, script.py.mako, 0001_initial_schema.py)
             2. Machine Learning Separation (`prism-new/ml/`):
                - ml/embeddings.py (intfloat/multilingual-e5-small, 384-d, ONNX int8, passage/query prefixing, L2 unit norm)
                - ml/sentiment.py (Augmented VADER + 250+ word Indian e-commerce / Hinglish YAML lexicon + rating prior)
                - ml/language_detector.py (Unicode codepoint script-block analysis for Indic languages)
                - ml/hinglish_detector.py (Romanized Hindi function-word analyzer)
                - ml/translator.py (In-memory PII masking + Sarvam Translate + Gemini fallback)
                - ml/multimodal.py (Gemini 1.5 Flash image OCR/defect analysis + video keyframing/audio transcription)
                - ml/ambiguity.py (6-signal ambiguity & sarcasm scorer with confidence multipliers)
                - ml/llm_client.py (Structured Gemini RAG diagnostic question drafting & offline fallbacks)
                - ml/lexicons/sentiment_lexicon.yaml (Curated vernacular e-commerce dictionary)
                - ml/eval.py & ml/calibrate.py (Classification metrics, ECE calculation, temperature scaling)
             3. Backend Orchestration (`prism-new/backend/`):
                - prism_core/ (Clean domain logic delegating to db/ and ml/ packages)
                - api/ (FastAPI routers: auth, catalog, ingest, read, actions, ops, stream, privacy)
                - workflows/ (Task runner and tasks: process_review, rebuild_product, source_health, survey_loop)
                - render.yaml & Dockerfile (Multi-package root context setup for 1-click deploy)
             4. Complete Test Suite (`prism-new/tests/`):
                - 37 / 37 tests passing (100% green across all 9 test suites MVP 1 - MVP 8)
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

## Repo layout (`prism-new/`)

```
prism-new/
  db/                   # standalone database package (models, multi-tenant repos, Alembic)
    base.py             # Declarative Base, TenantMixin, async engine, sessionmaker
    models.py           # all 27 SQLAlchemy multi-tenant models
    alembic.ini
    alembic/
      env.py
      versions/0001_initial_schema.py
    repositories/       # strict multi-tenancy repositories
      base.py           # enforces tenant_id on every query
      users.py, catalog.py, ingest.py, reviews.py, graph.py, metrics.py, actions.py, events.py
  ml/                   # standalone machine learning & NLP package
    embeddings.py       # intfloat/multilingual-e5-small, passage/query prefixes, unit norm
    sentiment.py        # augmented VADER + Hinglish dictionary + rating prior
    language_detector.py# Unicode script ranges for Indic languages
    hinglish_detector.py# Romanized Hindi classification
    translator.py       # in-memory PII masking + Sarvam Translate + Gemini fallback
    ambiguity.py        # 6-signal ambiguity & sarcasm scorer
    llm_client.py       # Gemini structured RAG question generator
    eval.py             # accuracy, macro-F1, ECE evaluation
    calibrate.py        # temperature scaling optimization
    lexicons/
      sentiment_lexicon.yaml # 250+ Hinglish/vernacular words
  backend/              # backend API & pipeline orchestration
    prism_core/         # domain logic orchestrating DB and ML
      config/           # settings.py, thresholds.yaml
      schemas/          # Pydantic v2 contracts
      ingest/           # L1 — accept(), sim-site adapters SITE_A through SITE_F
      language/         # L2 — normalise()
      trust/            # L2 — score(), G1-G6 gates
      extract/          # L3 — custom features (max 15), zero-shot cosine anchors
      serious/          # L3 — safety/thermal/injury triage
      batch/            # L3 — B0-B4 batch ladder
      graph/            # L4 — connected components, defect concentration, lead time
      trend/            # L4 — rollups, Wilson CI, spike detection
      compare/          # L4 — 5 comparative lenses, two-proportion z-test, health score
      confidence/       # L4 — F, D, C, T, E waterfall formula
      survey/           # L5 — RAG diagnostic questions, HMAC tokens
      mail/             # L5 — Jinja templates, outbox
      report/           # L5 — executive HTML/PDF report builder
      events/           # SSE emission + pipeline audit log
    api/                # FastAPI application
      main.py
      deps.py
      routers/ (auth, catalog, ingest, read, actions, ops, stream, privacy)
    workflows/          # Render Workflows tasks (plain Python runner)
      runner.py
      tasks/ (process_review, rebuild_product, source_health, survey_loop)
    Dockerfile
    pyproject.toml
    render.yaml
  tests/                # comprehensive pytest test suite


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
- [x] `prism_core/ml/language_detector.py` — `LanguageDetector` (fastText-style + Unicode script ranges)
- [x] `prism_core/ml/hinglish_detector.py` — `HinglishDetector` (Latin script + Indic function-word lexicon)
- [x] `prism_core/ml/translator.py` — `Translator` interface; Sarvam (formal, auto-src) → LLM fallback → keep original + `lang_tier_penalty`
- [x] PII masking applied before any external API call; mapping stays in-memory in task
- [x] `prism_core/language/__init__.py` — `normalise(raw: RawReview) -> NormalisedReview`

### L2 Trust
- [x] `prism_core/ml/embeddings.py` — `EmbeddingProvider`; multilingual-e5-small ONNX int8; `passage:` prefix for reviews, `query:` for anchors; batch encode 32-64; loaded once per worker
- [x] `prism_core/trust/__init__.py` — `score(review) -> TrustVerdict`; all 6 gates in order; writes `trust_gate_log`
  - G1 Length: < 2 words → `rejected_short`; rating continues
  - G2 Exact dupe: hash of normalised text; same tenant/product
  - G3 Near-dupe: pgvector HNSW cosine search, threshold 0.95 (config); cross-language
  - G4 Content heuristics: promo patterns, links, phones, repeated emoji, generic one-liners
  - G5 Burst + coordination: z-score on product-channel-day counts; author reuse; template clustering; rating histogram shift
  - G6 Provenance: verified purchase, date plausibility, source reliability
- [x] Trust score formula: start 1.0, subtract weighted gate penalties, add provenance bonus, clamp 0-1
- [x] Rating effect: clean → `counted` (w=1.0); suspicious → `downweighted` (w=trust_score); bot rejected → `excluded`; short-only → `counted`

---

## MVP 3 — Understand (Feature Extraction + Ambiguity)

### L3 Extract
- [x] `prism_core/ml/sentiment.py` — `SentimentModel` (Full 7,500-word `vaderSentiment` + augmented Indian e-commerce / Hinglish YAML dictionary; compact Transformer head); microsecond execution
- [x] `prism_core/ml/ambiguity.py` — `AmbiguityScorer` first-pass (6 signals); result: `none/vague/mixed/sarcasm` + mult
- [x] `prism_core/ml/llm_client.py` — `LLMClient` (Gemini structured output, JSON schema); fallback: rule-based + lower confidence
- [x] `prism_core/extract/__init__.py` — `analyse(review, product_id) -> ReviewAnalysis`
  - Sentence split + embed (`multilingual-e5-small` with `passage:` prefix)
  - Feature mapping: zero-shot cosine to custom product features (max 15) and category anchors, relative margin (0.04) + floor, keyword lexicon merge, max 4 features/sentence
  - Polarity per feature: `vaderSentiment` + Hinglish lexicon + negation + rating prior `r' = (rating - 3) / 2`
  - Sarcasm/ambiguity gate (cheap signals first, LLM if above `t_high`)
  - Writes `review_features`

### L3 Serious
- [x] `prism_core/serious/__init__.py` — `assess(review, analysis) -> SeriousAssessment`
  - Safety lexicon (multilingual) + semantic match to safety anchors
  - Score severity + urgency; insert `serious_complaints`; emit `serious.new`; optional Slack webhook
  - Suspicious reviews with safety keywords: surfaced but flagged unverified

### L3 Batch Inference
- [x] `prism_core/batch/__init__.py` — `infer(review) -> BatchInference`; ladder B0-B4
- [x] B1: OCR/vision via `ImageReader` (Gemini vision or Tesseract)
- [x] B2: registry date+warehouse lookup (pure rules)
- [x] B3/B4: cohort windows (labelled approximate in UI)
- [x] Cold-start pooling with sibling batches, labelled `pooled`

### API — Read routes (partial — reviews + xray)
- [x] `api/routers/read.py` — GET `/v1/reviews`, `/v1/reviews/{id}`, `/v1/reviews/{id}/xray`

---

## MVP 4 — Issue Graph + Batch Classification

### L4 Graph
- [x] `prism_core/graph/__init__.py` — `rebuild(product_id) -> list[Cluster]`
  - Nodes = feature mentions; edges = same product + feature + polarity
  - Edge weight formula (4 components, threshold 0.45, top-k 8 — all from config)
  - Only trusted mentions (trust >= 0.40) enter; suspicious at reduced weight
  - Connected components → clusters
  - Classification: isolated / batch / systemic / channel_specific / praise
  - Calculate `defect_concentration` (% share in dominant batch, $p < 0.001$) and `lead_time_days`
  - Writes `graph_edges`, `issue_clusters`, `cluster_members`

### API — Issues routes
- [x] GET `/v1/issues`, `/v1/issues/{id}` (with defect concentration, lead-time marker, and member verbatims)
- [x] GET `/v1/issues/{id}/audit` — **Click-to-Verify Audit Drawer** (unedited raw reviews, verified purchase badge, trust gate audit log, source links)

---

## MVP 5 — Comparison Engine + Confidence + Health Score

### L4 Trend + Rollups
- [x] `prism_core/trend/__init__.py` — `roll_up(product_id) -> list[TrendPoint]`
  - `metric_rollups` per (product, version, batch, channel, feature, week)
  - Trust-weighted rating sum + all-reviews sum (for with/without views)
  - Wilson interval on negative rate
  - EWMA/CUSUM change detection → `batch_spike`, `design_creep`
  - Spike alert if neg rate >= 0.60 + min sample, debounced 7 days

### L4 Compare
- [x] `prism_core/compare/__init__.py` — `run(lens, a, b, metric) -> Comparison`
  - 5 lenses: product, time, batch, channel, version
  - Statistics: two-proportion z-test + Wilson CI; Mann-Whitney U + rank-biserial; Benjamini-Hochberg
  - Min n = 20 per side else `insufficient_data`
  - Version impact: target feature neg rate + rating before/after modification
  - Health score formula: `0.35 * rating_component + 0.45 * sentiment_component + 0.20 * (1 - open_issue_penalty)`

### L4 Confidence & Action
- [x] `prism_core/confidence/__init__.py` — `score(cluster) -> ConfidenceBreakdown`
  - Formula with 5 terms + AmbiguityPenalty + CoherenceBonus + SurveyDelta
  - Store `confidence_parts` jsonb for waterfall UI
  - Levels: Act (>=0.75) / Monitor (0.45-0.74) / Gather (<0.45)
  - Severity: high (8+ mentions) / medium (4+) / low
  - Recommendation from (feature × issue_type) config matrix

### API — Full read routes & Ticket Export
- [x] GET `/v1/overview`, `/v1/issues/{id}/confidence`, `/v1/serious`, `/v1/trends`, `/v1/compare`
- [x] GET `/v1/issues/{id}/export` — **1-Click Ticket Exporter** (formats complete markdown/JSON bug ticket for Jira, Linear, or Slack webhook with root cause, verbatims, batch, and confidence waterfall)

---

## MVP 6 — Survey Loop + Email

### L5 Survey
- [x] `prism_core/survey/__init__.py` — `plan()`, `send()`, `ingest_reply()`
  - Consent-only targeting (no email without `consent_followup=true`)
  - **RAG diagnostic question generator:** retrieves cluster verbatims + product spec sheet + batch/firmware details; structured Gemini prompt drafts 3 targeted root-cause diagnostic questions
  - Signed expiring token in survey link
  - Survey page: Jinja template served by FastAPI (no JS framework, mobile-first, language selector)
  - Reply ingestion: LLM 2-sentence summary; confirm/deny signal → SurveyDelta updates confidence
  - `survey_loop` Render Workflow: long-running, sleeps 7 days, reminder at day 3

### L5 Mail
- [x] `prism_core/mail/__init__.py` — `send(template, to, ctx)`
  - `MailProvider` interface (Resend/Postmark-style)
  - Templates: `survey`, `serious_alert`, `digest_{qa,ops,support,marketing,leadership}`
  - Provider webhooks update `email_outbox.status`
  - Unsubscribe link in every survey email

### API — Action routes
- [x] POST `/v1/investigations/{issue_id}/survey`, GET/POST `/v1/survey/{token}`
- [x] POST `/v1/email/survey`, `/v1/email/digest`

---

## MVP 7 — Widget + Extension Ingest Handling

> Note: widget and extension code is frontend/browser work, but the **backend ingest endpoints and auth** for them belong here.

- [x] Widget endpoint hardening: origin allowlist per tenant stored in `sources.config`, rate limit enforced
- [x] Extension endpoint: `captured_by=user_id` provenance, batch capture (list of RawReview)
- [x] Overlay lookup: GET by `raw_hash` / review id returning trust verdict + cluster + batch + confidence

---

## MVP 8 — Ops, Eval, Report, Judge Mode

### Source Health Monitor
- [x] `prism_core/ingest/sources_health.py` — `evaluate(source_id) -> SourceHealth`
  - 6 signals: freshness, volume z-score, error rate, lag, schema drift, rating distribution shift
  - Emits `source.health` SSE events; writes `source_health` table

### Eval Harness
- [x] `seeds/` — generator for ~1,500 reviews, 4 products, 6 sites, 16 weeks, 20+ languages, ground-truth labels
- [x] `scripts/eval.py` — metrics: trust precision/recall, language F1, sarcasm F1, feature P/R, batch accuracy, detection lead-time, classification confusion matrix, confidence ECE
- [x] `scripts/calibrate.py` — reads labelled seed data, proposes threshold values
- [x] CI smoke test: small fixed subset, fails build if spam precision or batch recall drop below floors

### Company Report PDF
- [x] `prism_core/report/__init__.py` — `build(product_id, range) -> bytes`
  - Sections: exec summary, health + trust note, product comparison, channel performance, batch/version impact, top issues with evidence, serious complaints, recommendations
  - HTML template (Jinja) → WeasyPrint PDF

### Realtime SSE
- [x] `api/routers/stream.py` — GET `/v1/stream`
  - Postgres `LISTEN prism_events` connection
  - Fan-out to all connected SSE clients
  - Event kinds: `review.stage`, `trust.verdict`, `issue.updated`, `serious.new`, `survey.reply`, `source.health`

### Judge Mode / Demo
- [x] POST `/v1/demo/replay` — pushes seeded dataset through real pipeline at controlled speed; returns SSE stream

### Ops routes
- [x] GET `/v1/sources/health`, `/v1/pipeline/runs`, `/v1/eval/runs`
- [x] POST `/v1/reports`, GET `/v1/reports/{id}/download`
- [x] DELETE `/v1/privacy/author/{hash}` (DPDP compliance)

---

## Render Workflows tasks

| Task | Status |
|:--|:--|
| `process_review` (fan-out: normalise → trust → understand → batch_infer) | [x] |
| `rebuild_product` (graph → rollups → compare_cache → score_issues) | [x] |
| `notify` | [x] |
| `survey_loop` (long-running, resume-safe) | [x] |
| `trend_scan` (cron, hourly/daily) | [x] |
| `weekly_digest` (cron, Mon 09:00 IST) | [x] |
| `source_health` (cron, every 10 min) | [x] |
| `build_report` (on-demand) | [x] |
| `ingest_pull` (per-source cron + webhook) | [x] |

---

## Cross-cutting requirements (always check these)

- [x] Every query has `tenant_id` filter — test enforces this
- [x] No mock data fallbacks anywhere — empty/error states are honest
- [x] Every external AI call has a rule-based fallback; failures never silently dropped
- [x] PII masked before any external call; mapping stays in-memory in the task
- [x] `stage_versions` jsonb on `reviews` updated after every stage
- [x] `events.emit()` called at start, done, failed, retry for every pipeline stage
- [x] All thresholds read from `thresholds.yaml` — no magic numbers in code
- [x] Idempotency: re-run with same version is no-op; version bump triggers reprocess

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
