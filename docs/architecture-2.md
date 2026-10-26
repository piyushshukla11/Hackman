# PRISM Architecture

## 1. Principles

1. **Layered and modular.** Five layers (Ingest, Clean, Understand, Diagnose, Act). Each module exposes one public function with Pydantic input/output. Modules do not call each other's internals and do not write to each other's tables.
2. **Event-driven, durable, idempotent.** Ingest stores the raw event, then durable tasks process it. Every stage can be retried or re-run without duplicating results.
3. **Local first, LLM last.** Embeddings, rules, graph and statistics handle routine work. LLMs handle only ambiguous cases, survey drafting, and label/image OCR.
4. **Backend produces classified outputs.** The dashboard renders; it does not compute. Reports, digests and exports are generated in the backend.
5. **Honest data.** No mock fallbacks. Every metric shows how many reviews back it and how many were quarantined.

## 2. System context

```
 SOURCES                       RENDER                                        CONSUMERS
 6 sim sites (APIs) ──┐   ┌────────────────────────────────────────┐
 real APIs (later) ───┤   │  web service: FastAPI                   │   React dashboard (static)
 widget ──────────────┼──►│   - ingest gateway   - read API         │◄── widget / extension (clients)
 extension ───────────┤   │   - survey pages     - SSE stream       │◄── customer survey page
 CSV / JSON / email ──┘   │            │ enqueue                    │──► email provider (surveys, digests)
                          │            ▼                            │──► Slack webhook (serious alerts)
                          │  Render Workflows (Python tasks)        │
                          │   normalise → trust → extract → batch   │
                          │   → graph → trends → compare → score    │
                          │   cron: trend scan, digest, source health│
                          │   long-running: survey loop            │
                          │            │                            │
                          │  Postgres + pgvector (single DB)        │
                          └────────────────────────────────────────┘
```

## 3. Render services

| Service | Type | Notes |
| :-- | :-- | :-- |
| `prism-api` | Web service (Docker) | FastAPI, Alembic migrations as pre-deploy command |
| `prism-dashboard` | Static site | Vite build, talks to `prism-api` |
| `prism-workflows` | Render Workflows (Docker) | Python tasks, ML models loaded once per worker |
| `prism-db` | Postgres | pgvector extension enabled |
| Scheduled triggers | Workflows schedules or Render Cron Jobs | Confirm in Render docs which one triggers task runs |

Notes:
- Confirm the exact Workflows SDK syntax in Render docs before coding. Write task bodies as plain Python functions in `prism_core` and keep the Workflows decorator layer thin so it can be swapped.
- Docker runtime is chosen because of ML dependencies and WeasyPrint system libraries.
- Check worker instance memory. The quantised embedding model is about 120 MB; the fp32 model is about 470 MB. If memory is too tight, switch `EmbeddingProvider` to a hosted embedding API (interface in `ml.md`).
- Private networking between API, workflows and Postgres. Only the API and static site are public.

## 4. Python package map (`prism_core`)

| Module | Layer | Public function (input → output) | Owns tables |
| :-- | :-- | :-- | :-- |
| `ingest` | L1 | `accept(envelope) → raw_id` | `raw_reviews`, `sources` |
| `sources` (adapters) | L1 | `adapter.pull(cursor) → [RawReview]` | `sources.cursor` |
| `sources_health` | L1 | `evaluate(source_id) → SourceHealth` | `source_health` |
| `language` | L2 | `normalise(raw) → NormalisedReview` | part of `reviews` |
| `trust` | L2 | `score(review) → TrustVerdict` | `trust_gate_log` |
| `extract` | L3 | `analyse(review) → ReviewAnalysis` | `review_features` |
| `serious` | L3 | `assess(review, analysis) → SeriousAssessment` | `serious_complaints` |
| `batch` | L3 | `infer(review) → BatchInference` | `batches`, batch fields on `reviews` |
| `graph` | L4 | `rebuild(product_id) → [Cluster]` | `graph_edges`, `issue_clusters`, `cluster_members` |
| `trend` | L4 | `roll_up(product_id) → [TrendPoint]` | `metric_rollups`, `trend_points` |
| `compare` | L4 | `run(lens, a, b, metric) → Comparison` | reads rollups |
| `confidence` | L4 | `score(cluster) → ConfidenceBreakdown` | fields on `issue_clusters` |
| `survey` | L5 | `plan / send / ingest_reply` | `surveys`, `survey_responses` |
| `mail` | L5 | `send(template, to, ctx)` | `email_outbox` |
| `report` | L5 | `build(product_id, range) → pdf` | `reports` |
| `events` | shared | `emit(stage, status, ...)` | `pipeline_events` |

Rules for agents: modules import only from `prism_core.schemas`, `prism_core.config`, `prism_core.db` (repository helpers) and their own package. Cross-module data flows through the database or the typed objects passed by the task.

## 5. Data model (key tables and columns)

All tables carry `tenant_id` and `created_at`.

**Catalog**
- `products(id, name, category, taxonomy_id)`
- `product_versions(id, product_id, label, effective_from, notes)`
- `modifications(id, product_id, from_version, to_version, change_note, target_feature, target_issue_id?, effective_at)`
- `batches(id, product_id, version_id, code, mfg_start, mfg_end, ship_start, ship_end, warehouse, notes)`
- `feature_taxonomies(id, category, features jsonb)` (feature name, anchor phrases, keywords per language group)

**Ingestion**
- `sources(id, kind, adapter, display_name, config jsonb, cursor, enabled)`
- `source_health(source_id, checked_at, status, last_success_at, lag_seconds, items_24h, expected_24h, error_rate, schema_drift jsonb)`
- `raw_reviews(id, source_id, idempotency_key unique, kind, payload jsonb, received_at)` (append-only)

**Canonical review**
- `reviews(id, raw_id, product_id, source_id, channel, rating numeric(2,1), rating_raw, rating_scale, text_original, text_en, lang, script, reviewed_at, purchase_date, dispatch_date, warehouse, seller, verified_purchase, author_hash, media jsonb, batch_id, batch_method, batch_conf, version_id, text_status, rating_status, trust_score, ambiguity, ambiguity_mult, embedding vector(384), stage_versions jsonb)`
  - `text_status`: `accepted | rejected_short | rejected_spam | rejected_dup | none` (rating-only)
  - `rating_status`: `counted | downweighted | excluded`
- `review_features(review_id, feature, polarity, score, ambiguity, sentence_idx, anchor_sim)`
- `trust_gate_log(review_id, gate, verdict, reason_code, detail jsonb, score_delta)`

**Diagnosis**
- `graph_edges(src_review_id, dst_review_id, product_id, feature, weight)` (top-k per node)
- `issue_clusters(id, product_id, feature, polarity, issue_type, severity, confidence, confidence_parts jsonb, first_seen, last_seen, size, channels jsonb, batches jsonb, versions jsonb, status)`
- `cluster_members(cluster_id, review_id, role)`
- `metric_rollups(product_id, version_id, batch_id, channel, feature, week, n_reviews, n_neg, n_pos, rating_w_sum, rating_w, rating_n_all, rating_sum_all)` (the single source the comparison engine reads)
- `trend_points(product_id, feature, channel, window, n, neg_rate, neg_ci_low, neg_ci_high, rating_mean_trusted, rating_mean_all, pattern)`

**Action**
- `serious_complaints(id, review_id, category, severity, urgency, status, alerted_at)`
- `surveys(id, issue_id, review_id, token_hash, questions jsonb, status, expires_at)`, `survey_responses(survey_id, answers jsonb, summary, confidence_delta)`
- `email_outbox(id, template, to_hash, payload, status, provider_id, sent_at)`
- `alerts(id, product_id, kind, severity, message, triggered_at)`
- `reports(id, product_id, range, file_path, created_at)`
- `pipeline_events(id, run_id, review_id?, stage, status, attempt, duration_ms, detail, at)`
- `eval_runs(id, dataset, metrics jsonb, git_sha, at)`
- `returns_series(product_id, version_id?, batch_id?, week, returns_n, units_n, simulated bool)` (seeded for lead-time scoring; always labelled simulated in the UI)

Indexes: HNSW on `reviews.embedding` (cosine), btree on `(tenant_id, product_id, reviewed_at)`, unique on `idempotency_key`.

## 6. Classified backend outputs

Each output class has its own table, its own endpoint group and its own schema, so each interface consumes only what it needs.

| Output class | Contents | Source table | Endpoint |
| :-- | :-- | :-- | :-- |
| TrustVerdict | per-review gate results, trust score, reason codes | `trust_gate_log`, `reviews` | `/v1/trust/*`, `/v1/reviews/{id}/xray` |
| ReviewAnalysis | features, polarity, ambiguity, translation | `review_features` | `/v1/reviews/*` |
| IssueCard | feature, type, batch, channel, language, trend, confidence breakdown, evidence | `issue_clusters` | `/v1/issues/*` |
| SeriousComplaint | category, severity, urgency, status | `serious_complaints` | `/v1/serious/*` |
| Comparison | lens, groups, metric, delta, CI/p-value, verdict | `metric_rollups` | `/v1/compare` |
| TrendIndex / HealthIndex | weekly series, health scores | `trend_points`, rollups | `/v1/trends`, `/v1/overview` |
| Investigation | survey thread, replies, confidence change | `surveys` | `/v1/investigations/*` |
| Report / Digest | company report PDF, role digests | `reports`, `email_outbox` | `/v1/reports/*`, `/v1/email/*` |
| SourceHealth | per-source status | `source_health` | `/v1/sources/health` |

## 7. API surface (v1)

- **Auth:** `POST /auth/register|login|logout`, `GET /auth/me`; API keys: `POST /keys`
- **Ingest:** `POST /ingest/adapter/{source_id}` (webhook push), `POST /ingest/widget`, `POST /ingest/extension`, `POST /ingest/file` (CSV/JSON), `POST /ingest/email` (inbound parse webhook)
- **Catalog:** CRUD for `/products`, `/products/{id}/versions`, `/modifications`, `/batches`, `/sources`
- **Read:** `/overview`, `/reviews`, `/reviews/{id}/xray`, `/issues`, `/issues/{id}`, `/issues/{id}/confidence`, `/serious`, `/trends`, `/compare?lens=product|time|batch|channel|version`
- **Action:** `POST /investigations/{issue_id}/survey` (manual trigger), `GET /survey/{token}` and `POST /survey/{token}` (public, tokenised), `POST /email/survey`, `POST /email/digest`, `POST /reports`, `GET /reports/{id}/download`
- **Ops:** `GET /sources/health`, `GET /pipeline/runs`, `GET /eval/runs`, `POST /demo/replay` (replays the seeded dataset through the real pipeline)
- **Realtime:** `GET /stream` (SSE)

Conventions: JSON, cursor pagination, all responses include `n` (support count) and `quarantined_n` where aggregates are returned.

## 8. Realtime events

Workflow tasks call `events.emit(...)`, which inserts into `pipeline_events` and issues `NOTIFY prism_events`. The API holds a `LISTEN` connection and fans out via SSE. Event kinds: `review.stage` (stage, status, attempt, duration), `trust.verdict`, `issue.updated`, `serious.new`, `survey.reply`, `source.health`. The Prism Stream visual consumes exactly these; a retry on screen is a real retry in the Render task run.

## 9. Auth, tenancy, roles

- Email + password, bcrypt, HttpOnly JWT cookie (8h). No hardcoded credentials; a seed script creates demo users.
- `tenant_id` on every table and every query (enforced in repository helpers; add a test that fails if a query lacks it).
- Roles: `admin` (settings, keys, products), `member` (read, trigger surveys). Role *lenses* (QA, ops, support, marketing, leadership) are a UI view setting and the digest audience, not a permission level.
- Widget uses a public key with an origin allowlist. Extension uses a user-scoped token. Ingestion servers use secret API keys (hashed at rest).

## 10. Email module

One module, used by surveys, serious alerts and digests.
- Templates (Jinja, inline-CSS): `survey`, `serious_alert`, `digest_{qa,ops,support,marketing,leadership}`.
- Provider API behind `MailProvider` interface (Resend or Postmark style). Provider webhooks update `email_outbox.status` (sent, delivered, bounced).
- Survey links carry a signed, expiring token. Every survey email has an unsubscribe link and is sent only where consent was captured.
- Digests are generated by the weekly cron task per tenant and role.
- Exposed through `/v1/email/*` so external systems can request a survey or digest.

## 11. Privacy and security

- PII masking (emails, phones, order IDs, addresses, names where detected) before any external AI call. The mapping stays local.
- Retention: raw text retention is configurable (default 180 days); `DELETE /v1/privacy/author/{hash}` removes a person's data on request. Designed with India's DPDP Act in mind (consent-based surveys, limited retention, purpose limitation).
- Secrets only in Render environment groups. Webhook signatures verified. Rate limits on public endpoints (ingest, survey).

## 12. CI/CD

- GitHub Actions on push/PR: lint (ruff), type check (mypy, light), unit tests (pytest), **eval smoke test** (small seeded set; fails if spam precision or batch recall drops below floor), dashboard type check and build, extension and widget build.
- Render Blueprint (`render.yaml`) defines all services; auto-deploy on `main`; Alembic runs as pre-deploy.

## 13. Configuration

`prism_core/config/thresholds.yaml` holds every tunable number (duplicate similarity, spam weights, edge threshold, cluster rules, confidence weights, health score weights, min sample sizes). `scripts/calibrate.py` proposes values from the labelled seed data. Defaults are marked *initial* in `ml.md` and must be calibrated, not trusted.

## 14. Failure handling

- Each task retries with exponential backoff (default 3 attempts); after the last attempt the review gets `stage_status=failed` and appears in the pipeline view.
- Idempotency: `idempotency_key` on raw events; each stage records its version in `stage_versions`, so a re-run with the same version is a no-op and a version bump reprocesses.
- Adapters are isolated: one failing source does not stop others, and `source_health` records it.
- External AI call fails: rule-based fallback result is stored with a lower confidence flag; never silently dropped.

## 15. Interfaces and their stacks

| Interface | Audience | Stack |
| :-- | :-- | :-- |
| Dashboard | Brand teams, judges | React, Vite, TypeScript, Tailwind, shadcn/ui |
| Widget | Small companies' customers | Vanilla TypeScript, single bundle |
| Extension | Authorised staff | Chrome MV3, TypeScript |
| Survey page | Customers | Server-rendered (Jinja) from FastAPI, no JS framework |
| Simulated sites (6, placeholders) | Demo and tests | Small Node or static apps, each with a different review-API shape |
| Reports and digests | Leadership, teams | Backend-generated PDF and HTML email |
