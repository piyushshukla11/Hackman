# PRISM Contracts

All public interfaces in PRISM — module signatures, REST endpoints, SSE events, Render Workflow tasks, and inter-module data-flow rules.

> **Rule:** Every module in `prism_core` exposes **one** public function with a Pydantic input and a Pydantic output. Modules do **not** call each other's internals and do **not** write to each other's tables. Cross-module data flows through the database or through typed objects passed by the Render Workflow task.

---

## 1. Module contracts (`prism_core`)

### 1.1 L1 — Ingest

#### `ingest.accept`
```python
def accept(envelope: RawReview) -> RawID
```
- Validates the `RawReview` envelope, computes `idempotency_key`, writes to `raw_reviews`, enqueues `process_review`.
- **Idempotency key:** `sha256(tenant | source | source_review_id)` — when no source review id: `sha256(tenant | source | product | author_hash | reviewed_at | normalised_text)`.
- Duplicate key → no-op (returns existing `raw_id`).
- Owns tables: `raw_reviews`, `sources`.

#### `sources.adapter` — `ReviewSource` protocol
```python
class ReviewSource(Protocol):
    id: str
    def pull(self, cursor: str | None) -> tuple[list[RawReview], str | None]: ...
    def handle_webhook(self, payload: bytes, headers: dict) -> list[RawReview]: ...
    def health_probe(self) -> ProbeResult: ...
```
- Owns: `sources.cursor`.
- All 6 sim-site adapters and all future real adapters implement this protocol.

#### `sources_health.evaluate`
```python
def evaluate(source_id: str) -> SourceHealth
```
- Owns table: `source_health`.

---

### 1.2 L2 — Clean

#### `language.normalise`
```python
def normalise(raw: RawReview) -> NormalisedReview
```
```python
class NormalisedReview(BaseModel):
    lang: str          # BCP 47 with script tag e.g. "hi-Latn"
    script: str        # "Latin" | "Devanagari" | ...
    text_original: str
    text_en: str       # translated if non-English; same as original if English
    emojis: list[str]
    lang_tier: Literal[1, 2, 3]
    lang_tier_penalty: bool
```
- Writes into the `reviews` table (lang/script columns).

#### `trust.score`
```python
def score(review: NormalisedReview) -> TrustVerdict
```
```python
class TrustVerdict(BaseModel):
    trust_score: float           # 0.0 – 1.0
    verdict: Literal["clean", "suspicious", "rejected"]
    text_status: Literal["accepted", "rejected_short", "rejected_spam", "rejected_dup", "none"]
    rating_status: Literal["counted", "downweighted", "excluded"]
    gates: list[GateResult]

class GateResult(BaseModel):
    gate: Literal["G1", "G2", "G3", "G4", "G5", "G6"]
    verdict: Literal["pass", "warn", "fail"]
    reason_code: str   # e.g. SHORT_TEXT, NEAR_DUP, PROMO, BURST, TEMPLATE, RATING_SPIKE
    score_delta: float
    detail: dict
```
- Owns table: `trust_gate_log`.

---

### 1.3 L3 — Understand

#### `extract.analyse`
```python
def analyse(review: NormalisedReview, product_id: str | None = None) -> ReviewAnalysis
```
```python
class FeatureMention(BaseModel):
    feature: str
    polarity: Literal["pos", "neg", "neutral"]
    score: float
    ambiguity: Literal["none", "vague", "mixed", "sarcasm"]
    ambiguity_mult: float       # 1.00 / 0.85 / 0.70 / 0.55
    sentence_idx: int
    anchor_sim: float
    llm_used: bool
    needs_second_opinion: bool

class ReviewAnalysis(BaseModel):
    features: list[FeatureMention]
    embedding: list[float]      # 384-d multilingual-e5-small
    serious: SeriousAssessment | None
    sentiment_engine: Literal["vader_augmented", "transformer_head", "llm_second_pass"]
```
- **Embeddings:** `intfloat/multilingual-e5-small` (384-d, ONNX int8). Uses `passage:` prefix for reviews and `query:` prefix for anchors.
- **Company Custom Features (Max 15):** Tenants can input up to 15 custom feature words/phrases per product (e.g. "ear cushion comfort", "fizz", "hinge sturdiness"). Matched zero-shot in the same vector space with auto-anchor variations.
- **Feature mapping:** Cosine against product custom features (max 15) + category anchors; relative margin (0.04) + calibrated floor; max 4 features per sentence.
- **Polarity:** Full 7,500-word `vaderSentiment` engine augmented with custom Indian e-commerce / Hinglish dictionary (`sentiment_lexicon.yaml`) + negation rules + rating prior `r' = (rating - 3) / 2`.
- **Ambiguity:** First-pass 6 signals; if above `t_high`, Gemini structured output second pass.
- Owns table: `review_features`.

#### `serious.assess`
```python
def assess(review: NormalisedReview, analysis: ReviewAnalysis) -> SeriousAssessment
```
```python
class SeriousAssessment(BaseModel):
    category: str
    severity: Literal["high", "medium", "low"]
    urgency: Literal["high", "medium", "low"]
    status: Literal["open", "escalated", "resolved"]
    alerted_at: datetime | None
```
- Owns table: `serious_complaints`.
- Emits `serious.new` SSE event.

#### `batch.infer`
```python
def infer(review: NormalisedReview) -> BatchInference
```
```python
class BatchInference(BaseModel):
    batch_id: str | None
    batch_method: Literal["B0", "B1", "B2", "B3", "B4"]
    batch_conf: float           # 1.00 / 0.85 / 0.70 / 0.50 / 0.30
    version_id: str | None
    pooled: bool
```
- Owns tables: `batches`; writes `batch_id`, `batch_method`, `batch_conf`, `version_id` onto `reviews`.

---

### 1.4 L4 — Diagnose

#### `graph.rebuild`
```python
def rebuild(product_id: str) -> list[Cluster]
```
```python
class Cluster(BaseModel):
    id: str
    product_id: str
    feature: str
    polarity: Literal["neg", "pos"]
    issue_type: Literal["isolated", "batch", "systemic", "channel_specific", "praise"]
    severity: Literal["high", "medium", "low"]
    first_seen: date
    last_seen: date
    size: int
    channels: dict[str, int]
    batches: dict[str, float]   # batch_id -> confidence-weighted share
    versions: list[str]
    defect_concentration: float # % share in dominant batch (e.g. 0.82 = 82% of complaints in one batch)
    dominant_batch_id: str | None
    p_value: float              # statistical significance (e.g. p < 0.001)
    lead_time_days: int         # days detected ahead of marketplace rating/returns spike
```
- Edge weight formula:
  ```
  weight = 0.40 * semantic_similarity
         + 0.25 * time_proximity        (1 - days_apart / 28, floor 0)
         + 0.25 * batch_affinity        (1 same batch | 0.6 same version | 0.3 same cohort)
         + 0.10 * symptom_overlap
  edge if weight >= 0.45 (thresholds.yaml); keep top-k (8) per node
  ```
- Owns tables: `graph_edges`, `issue_clusters`, `cluster_members`.

#### `trend.roll_up`
```python
def roll_up(product_id: str) -> list[TrendPoint]
```
- Maintains `metric_rollups` per `(product, version, batch, channel, feature, week)`.
- Emits spike alerts via `alerts` table when negative rate >= 0.60 (config).
- Owns tables: `metric_rollups`, `trend_points`.

#### `compare.run`
```python
def run(
    lens: Literal["product", "time", "batch", "channel", "version"],
    a: str,
    b: str,
    metric: Literal["rating", "neg_rate", "health_score"]
) -> Comparison
```
```python
class Comparison(BaseModel):
    lens: str
    a: str
    b: str
    metric: str
    delta: float
    ci_low: float
    ci_high: float
    p_value: float
    n_a: int
    n_b: int
    verdict: Literal["better", "worse", "no_change", "insufficient_data"]
    top_features: list[str]
```
- Reads only from `metric_rollups` — never touches raw reviews.
- Statistics: two-proportion z-test + Wilson CI (rates); Mann-Whitney U + rank-biserial (ratings); Benjamini-Hochberg for multiple comparisons.
- Min n = 20 per side (config) else `insufficient_data`.

#### `confidence.score`
```python
def score(cluster: Cluster) -> ConfidenceBreakdown
```
```python
class ConfidenceBreakdown(BaseModel):
    frequency: float
    density: float
    consistency: float
    temporal: float
    evidence: float
    ambiguity_penalty: float
    coherence_bonus: float
    survey_delta: float
    final: float                # clamped 0-1
    level: Literal["act", "monitor", "gather"]   # >=0.75 / 0.45-0.74 / <0.45
```
- Formula: `base = 0.25*F + 0.20*D + 0.20*C + 0.15*T + 0.20*E; final = clamp(base * AmbiguityPenalty + CoherenceBonus + SurveyDelta, 0, 1)`.
- Stored in `issue_clusters.confidence_parts` (jsonb) for UI waterfall.

---

### 1.5 L5 — Act

#### `survey` module
```python
def plan(issue_id: str, trigger: str) -> Survey
def send(survey_id: str) -> None
def ingest_reply(survey_id: str, answers: dict) -> SurveyDelta
```
- **RAG-Grounded Diagnostic Question Drafting:**
  - **Retrieval:** Pulls top 4 verbatim customer quotes from cluster members, product technical specs from `products.specs`, and identified batch/firmware details.
  - **Prompt Augmentation:** Injects retrieved context into Gemini structured prompt to generate 3 targeted diagnostic multiple-choice questions (e.g. isolating sudden voltage drop vs gradual battery drain, or hinge screw torque vs plastic fatigue).
  - **Fallback:** If LLM is unavailable or low-confidence, falls back to category-calibrated diagnostic templates.
- Owns tables: `surveys`, `survey_responses`.

#### `mail.send`
```python
def send(template: str, to: str, ctx: dict) -> None
```
- Templates: `survey`, `serious_alert`, `digest_{qa,ops,support,marketing,leadership}`.
- Owns table: `email_outbox`.

#### `report.build`
```python
def build(product_id: str, range: tuple[date, date]) -> bytes  # PDF bytes
```
- Owns table: `reports`.

---

### 1.6 Shared

#### `events.emit`
```python
def emit(
    stage: str,
    status: Literal["started", "done", "failed", "retry"],
    run_id: str,
    review_id: str | None = None,
    **detail
) -> None
```
- Inserts into `pipeline_events` and issues `NOTIFY prism_events` (Postgres).
- Owns table: `pipeline_events`.

---

## 2. Pydantic schemas (shared, in `prism_core.schemas`)

### `RawReview` (the envelope)
```python
class RawReview(BaseModel):
    tenant_id: str
    source_id: str
    channel: str
    kind: Literal["review", "rating_only"]
    source_review_id: str | None
    product: ProductRef           # sku or external_id required
    rating: RatingPayload         # value in {0.5, 1.0, ..., 5.0} after normalisation
    text: str | None
    title: str | None
    reviewed_at: datetime
    author: AuthorPayload
    order: OrderPayload | None
    batch_code: str | None
    media: list[MediaItem]
    contact: ContactPayload | None
    provenance: ProvenancePayload
```
**Required fields:** `tenant_id`, `source_id`, `product` (sku or external_id), `rating`, `reviewed_at`.

### `MediaItem` & Multimodal Processing Contract
```python
class MediaItem(BaseModel):
    media_id: str
    kind: Literal["image", "video"]
    url: str
    transcript: str | None = None       # extracted spoken audio text
    keyframes: list[str] = []           # captured candidate frame URLs (max 3)
    ocr_text: str | None = None         # barcode/serial label text if detected
```
- **Cost-Efficient Multimodal Strategy (Hackathon-Feasible):**
  - **Images:** Scaled to 768px max dimension before ingestion.
  - **Videos (Audio Track First):** Audio track extracted via `ffmpeg` → Sarvam/Whisper STT converts spoken complaints to text in seconds (90% cheaper than raw video LLM tokens).
  - **Videos (Keyframe Capture):** 3 representative keyframes extracted at scene transitions / equidistant timestamps (25%, 50%, 75%).
  - **Selective Vision Filter:** Candidate frames/images are only routed to Gemini Vision if: (1) review text/audio triggers visual defect keywords (`"cracked"`, `"burnt"`, `"smoke"`, `"shattered"`, `"bent"`), or (2) label OCR is required for batch inference (B1). Otherwise, Vision LLM is skipped ($0 token waste).

### Rating normalisation (applied per adapter before producing `RawReview`)
| Source scale | Mapping |
|:--|:--|
| 5 integer stars | as-is |
| 5 with half-stars | as-is |
| 10-point | `round(x / 2 * 2) / 2` — nearest 0.5 |
| 100-point | `x / 20` then nearest 0.5 |
| Thumbs up/down | 4.5 / 1.5 with `derived=true` |
| Sentiment label only | not accepted as rating; text only |

---

## 3. REST API — v1

All responses are JSON. Aggregates include `n` (support count) and `quarantined_n`. Pagination is cursor-based.

### Auth
| Method | Path | Description |
|:--|:--|:--|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Returns HttpOnly JWT cookie (8 h) |
| POST | `/auth/logout` | Clear cookie |
| GET | `/auth/me` | Current user, `role_title`, `selected_views`, `has_completed_onboarding` |
| POST | `/auth/onboarding` | First-login setup: saves `role_title` (e.g. "Senior QA Lead") and `selected_views` |
| PATCH | `/auth/me/preferences` | Update visible views or switch demo persona (QA, CX, PM, Exec) |
| POST | `/keys` | Create API key (admin) |

### Ingest
| Method | Path | Description |
|:--|:--|:--|
| POST | `/v1/ingest/adapter/{source_id}` | Webhook push from adapter |
| POST | `/v1/ingest/widget` | Widget submission (public key + origin check) |
| POST | `/v1/ingest/extension` | Extension batch (user-scoped token) |
| POST | `/v1/ingest/file` | CSV / JSON upload |
| POST | `/v1/ingest/email` | Inbound email parse webhook |

### Catalog (CRUD)
| Method | Path | Description |
|:--|:--|:--|
| GET/POST | `/v1/products` | Product management |
| GET/PUT/DELETE | `/v1/products/{id}` | Product detail |
| GET/POST | `/v1/products/{id}/versions` | Product versions |
| GET/POST | `/v1/products/{id}/features` | **Company Custom Features (max 15)**: get or set custom features |
| GET/POST | `/v1/modifications` | Modifications |
| GET/POST | `/v1/batches` | Manufacturing batches |
| GET/POST | `/v1/sources` | Ingestion sources |

### Read
| Method | Path | Returns |
|:--|:--|:--|
| GET | `/v1/overview` | `TrendIndex`, `HealthIndex`, top issues, alerts count |
| GET | `/v1/reviews` | Paginated reviews (filters: product, channel, lang, trust) |
| GET | `/v1/reviews/{id}` | Single review + `ReviewAnalysis` |
| GET | `/v1/reviews/{id}/xray` | Full X-ray: gate log, anchor sims, batch inference, translation diff |
| GET | `/v1/issues` | Paginated `IssueCard` list |
| GET | `/v1/issues/{id}` | Single `IssueCard` with member list, `defect_concentration` & `lead_time_days` |
| GET | `/v1/issues/{id}/audit` | **Click-to-Verify Audit Drawer**: unedited raw reviews, verified purchase proof, trust gate audit log, and source links |
| GET | `/v1/issues/{id}/confidence` | `ConfidenceBreakdown` (waterfall data) |
| GET | `/v1/issues/{id}/export` | **1-Click Ticket Exporter**: formatted Jira/Linear/Slack markdown & JSON |
| GET | `/v1/serious` | Serious-complaint queue |
| GET | `/v1/trends` | `TrendPoint[]` per product/feature/channel |
| GET | `/v1/compare` | `Comparison` — `?lens=product|time|batch|channel|version&a=&b=&metric=` |

### Action
| Method | Path | Description |
|:--|:--|:--|
| POST | `/v1/investigations/{issue_id}/survey` | Manual survey trigger |
| GET | `/v1/survey/{token}` | Public survey page (tokenised, Jinja) |
| POST | `/v1/survey/{token}` | Submit survey answers (public) |
| POST | `/v1/email/survey` | Send survey email via external request |
| POST | `/v1/email/digest` | Send digest email |
| POST | `/v1/reports` | Generate company report PDF |
| GET | `/v1/reports/{id}/download` | Download PDF |

### Ops
| Method | Path | Description |
|:--|:--|:--|
| GET | `/v1/sources/health` | `SourceHealth[]` |
| GET | `/v1/pipeline/runs` | Recent pipeline event log |
| GET | `/v1/eval/runs` | Eval harness results |
| POST | `/v1/demo/replay` | Replay seeded dataset through real pipeline (Judge mode) |

### Privacy
| Method | Path | Description |
|:--|:--|:--|
| DELETE | `/v1/privacy/author/{hash}` | Remove a person's data on request (DPDP) |

### Realtime
| Method | Path | Description |
|:--|:--|:--|
| GET | `/v1/stream` | SSE stream — see section 4 |

---

## 4. SSE event contracts (`/v1/stream`)

The API holds a `LISTEN prism_events` connection on Postgres and fans events out to SSE clients.

| Event kind | Payload fields | Consumed by |
|:--|:--|:--|
| `review.stage` | `stage, status, attempt, duration_ms, review_id, run_id` | Prism Stream visual |
| `trust.verdict` | `review_id, verdict, trust_score, reason_codes[]` | Prism Stream |
| `issue.updated` | `issue_id, product_id, confidence, issue_type` | Issues list, waterfall |
| `serious.new` | `complaint_id, review_id, severity, urgency` | Serious queue |
| `survey.reply` | `survey_id, issue_id, confidence_before, confidence_after` | Survey thread |
| `source.health` | `source_id, status, error_rate, lag_seconds` | Sources page |

---

## 5. Render Workflow task contracts

Each task is a thin decorator over a plain Python function in `prism_core`. Task bodies **must** be swappable if the Render Workflows SDK changes.

| Task | Input | Output | Trigger | Retries |
|:--|:--|:--|:--|:--|
| `ingest_pull(source_id)` | `source_id: str` | `list[RawID]` | cron per source / webhook | 3, backoff |
| `process_review(raw_id)` | `raw_id: str` | `ReviewResult` | enqueued by gateway (fan-out) | 3, backoff |
| `normalise(raw_id)` | `raw_id` | `NormalisedReview` | subtask of process_review | per stage |
| `trust(review_id)` | `review_id` | `TrustVerdict` | subtask | per stage |
| `understand(review_id)` | `review_id` | `ReviewAnalysis` | subtask | per stage |
| `batch_infer(review_id)` | `review_id` | `BatchInference` | subtask | per stage |
| `rebuild_product(product_id)` | `product_id: str` | `None` | after fan-out | 3, backoff |
| `graph(product_id)` | `product_id` | `list[Cluster]` | subtask of rebuild | per stage |
| `rollups(product_id)` | `product_id` | `None` | subtask | per stage |
| `compare_cache(product_id)` | `product_id` | `None` | subtask | per stage |
| `score_issues(product_id)` | `product_id` | `None` | subtask | per stage |
| `notify(product_id)` | `product_id` | `None` | after rebuild | 3 |
| `survey_loop(issue_id)` | `issue_id: str` | `SurveyDelta` | issue in Monitor/Gather or manual | resume-safe, long-running |
| `trend_scan` | _(none)_ | `None` | cron (hourly/daily) | 2 |
| `weekly_digest` | _(none)_ | `None` | cron (Mon 09:00 IST) | 3 |
| `source_health` | _(none)_ | `SourceHealth[]` | cron (every 10 min) | 1 |
| `build_report(product_id, range)` | `product_id, range` | `bytes` (PDF) | API request | 2 |

All tasks call `events.emit(stage, status, ...)` at start, completion and failure so `pipeline_events` and the SSE stream are always consistent.

---

## 6. Output class contracts

Each output class has its own table, endpoint group, and schema.

| Output class | Key fields | Source tables | Endpoint group |
|:--|:--|:--|:--|
| `TrustVerdict` | trust_score, verdict, gates[] | `trust_gate_log`, `reviews` | `/v1/trust/*`, `/v1/reviews/{id}/xray` |
| `ReviewAnalysis` | features[], embedding, ambiguity | `review_features` | `/v1/reviews/*` |
| `IssueCard` | feature, type, batch, channel, lang, trend, confidence | `issue_clusters` | `/v1/issues/*` |
| `SeriousComplaint` | category, severity, urgency, status | `serious_complaints` | `/v1/serious/*` |
| `Comparison` | lens, delta, CI, p-value, verdict | `metric_rollups` | `/v1/compare` |
| `TrendIndex / HealthIndex` | weekly series, health_score (0-100) | `trend_points`, rollups | `/v1/trends`, `/v1/overview` |
| `Investigation` | survey thread, replies, confidence_delta | `surveys` | `/v1/investigations/*` |
| `Report / Digest` | PDF bytes, HTML email | `reports`, `email_outbox` | `/v1/reports/*`, `/v1/email/*` |
| `SourceHealth` | status, lag, error_rate, schema_drift | `source_health` | `/v1/sources/health` |

---

## 7. Auth and tenancy contracts

- **JWT cookie** — HttpOnly, 8 h, `bcrypt`-hashed password. No hardcoded credentials; seed script creates demo users.
- **`tenant_id`** — present on every table and every query. Repository helpers enforce it; a test **must** fail if any query omits it.
- **Roles:** `admin` (settings, keys, products) | `member` (read, trigger surveys).
- **First-Login Role Onboarding:** On first login, user inputs their `role_title` (e.g. "Senior QA Lead", "Head of Product", "Customer Experience Lead") and selects which modules they want displayed. The dashboard navigation and view layout adapt to avoid clutter.
- **Demo Persona Quick-Switcher:** Judges/users can switch between preset personas (QA, Support/CX, Product Manager, Executive) with 1 click to view role-tailored lenses.
- **Widget:** public key + origin allowlist + rate limit.
- **Extension:** user-scoped token; revocable; domain allowlist per tenant.
- **Adapters:** secret API keys, hashed at rest.
- **Survey links:** signed, expiring token. Unsubscribe link in every survey email.

---

## 8. Versioning and idempotency contracts

- `reviews.stage_versions` (jsonb) records the module version that ran each stage.
- Bumping a `STAGE_VERSION` triggers `reprocess(product_id, from_stage)` — only that stage and later stages re-run.
- A re-run with the **same** version is a no-op. A version bump reprocesses.
- The same review arriving via two lanes (e.g. API + extension) is deduplicated by `raw_hash` at the gateway and again by G2/G3 trust gates.

---

## 9. Config and threshold contracts

All tunable numbers live in `prism_core/config/thresholds.yaml`. No magic numbers in code.

| Parameter | Initial value |
|:--|:--|
| Min words for text (G1) | 2 |
| Near-duplicate similarity (G3) | 0.95 |
| Trust clean cut | >= 0.70 |
| Trust suspicious range | 0.40 - 0.69 |
| Trust rejected cut | < 0.40 |
| Feature relative margin | 0.04 |
| Graph edge threshold | 0.45 |
| Top-k edges per node | 8 |
| Isolated issue size | < 3 |
| Batch rule | >= 4 mentions, >= 70% one batch, <= 21 days, p < 0.01 |
| Systemic rule | >= 3 batches or > 6 weeks, >= 2 channels |
| Channel-specific | >= 80% one channel |
| Confidence weights | F 0.25 / D 0.20 / C 0.20 / T 0.15 / E 0.20 |
| Confidence act level | >= 0.75 |
| Confidence monitor level | 0.45 - 0.74 |
| Min n for comparisons | 20 per side |
| Negative-rate spike alert | >= 0.60 with min sample |
| Health score weights | rating 0.35 / sentiment 0.45 / issue penalty 0.20 |
| Ambiguity multipliers | none 1.00 / vague 0.85 / mixed 0.70 / sarcasm 0.55 |

`scripts/calibrate.py` proposes revised values from the labelled seed data. CI smoke tests fail if spam precision or batch recall drop below configured floors.

---

## 10. Render deployment and Workflows budget

### What Render Workflows is (for reference)
Render Workflows is Render's managed background task system. You write plain Python functions; the Render SDK wraps them as durable tasks that run on a worker container. Features used by PRISM:
- **Fan-out:** kick off N tasks in parallel from one trigger (one task per review from the ingest gateway)
- **Sequential subtasks:** chain normalise → trust → understand → batch_infer inside one `process_review` run
- **Retries with backoff:** 3 attempts per stage by default, all config-driven
- **Cron schedules:** source_health (every 10 min), trend_scan, weekly_digest
- **Long-running tasks:** survey_loop sleeps and resumes (up to 7 days) without holding a thread

Task bodies live in `prism_core` as plain Python functions. The Render SDK decorator is a **thin wrapper only** — tasks must be fully testable without Render and swappable if the SDK changes.

> **Before coding any Render-specific feature (fan-out API, long-running sleep, cron syntax) — read the Render Workflows SDK docs first. Never assume syntax.**

---

### Render services (from `render.yaml`)

| Service name | Render type | What runs | Always-on? |
|:--|:--|:--|:--|
| `prism-db` | Managed Postgres | pgvector-enabled database | Yes |
| `prism-api` | Web service (Docker) | FastAPI app; Alembic pre-deploy | Yes |
| `prism-workflows` | Workflows worker (Docker) | All pipeline + cron tasks | Scales to 0 when idle |
| `prism-dashboard` | Static site | Vite-built React app | Free (CDN) |
| `prism-sim-*` | Static sites or small web services | 6 placeholder storefronts | Free/minimal |

---

### Account split strategy ($35 × 4 accounts = $140 total)

> **Zero-Break Demo Workaround:** Render Private Networking only functions within the same account. Cross-account calls traverse the public internet (adding latency, SSL handshake overhead, and failure points). To guarantee the live demo never breaks, **all live production services (`prism-db`, `prism-api`, `prism-workflows`) are co-located in Account 1 (PROD)**. Internal DNS (`prism-db:5432`) gives sub-millisecond, isolated, rock-solid connections. The remaining 3 accounts are utilized cleanly for Dev, Simulators, and a Hot Standby.

| Account | Label | Hosts | Rationale | Budget |
|:--|:--|:--|:--|:--|
| **A1** | **PROD (Live Demo)** | `prism-db` (Postgres starter, $7/mo), `prism-api` (starter web service, $7/mo), `prism-workflows` (worker, task-sec), `prism-dashboard` (static CDN, free) | **Zero demo breakage**: 100% Render Private Networking. Never touches public internet for DB or task queues. | ~$5 total (<$35) |
| **A2** | **DEV / STAGING** | Development mirror of `prism-api` & `prism-workflows` | Unrestricted sandbox to test Workflows code, dry-run tasks, and smoke test without dirtying demo DB | ~$10 max |
| **A3** | **SIMULATORS & MOCKS** | External data feeders (Shopify webhook generator, mock Play Store reviews crawler) | Runs data generation traffic and mock external services, isolating noise from demo DB | ~$10 max |
| **A4** | **HOT STANDBY (Backup)** | 1-click clone of `render.yaml` Blueprint (dormant / pre-configured) | Ultimate demo safety net: instant fallback if Account 1 ever hits an unexpected quota or platform incident | $0 ($35 reserve) |

**Estimated hackathon cost (production A1):**
- Postgres starter: ~$7/mo (prorated for hackathon duration, < $2)
- API web service starter: ~$7/mo (prorated, < $2)
- Workflows worker: billed per task-second of execution; ~1,500 seed reviews × ~2 s/review pipeline = ~3,000 task-seconds (< $1)
- Total expected: **< $5** on A1, leaving >$30 buffer on A1 alone!

**Demo Safety & Fallback Rules:**
- **Zero cross-account dependencies on PROD**: API and Workflows connect to DB via private host `prism-db:5432`.
- **Local Fallback**: Task functions in `prism_core` are decoupled pure Python functions; if Render or conference Wi-Fi experiences downtime during judging, backend runs seamlessly locally via Docker Compose or `uvicorn main:app`.
- **Budget guardrail**: Workflows worker scales to 0 when idle; seed replay runs only on PROD.

---

### Render Workflows judge story (what judges see)

This is the narrative for the Render Workflows track submission:

1. **Ingest gateway** receives a review → immediately enqueues `process_review` as a Render Workflow task
2. **Fan-out** — for a batch of reviews, the gateway fans out N tasks in parallel; Render handles queuing and concurrency
3. **Sequential pipeline** — each `process_review` task runs: normalise → trust → extract → batch_infer as subtasks; each stage is retried independently on failure
4. **Product rebuild** — after the fan-out completes, `rebuild_product` fires: graph → rollups → compare_cache → score_issues
5. **Cron tasks** — source_health runs every 10 min, trend_scan daily, weekly_digest Monday 09:00 IST; all defined in `render.yaml`
6. **Long-running survey loop** — `survey_loop` is a long-running Workflows task: sends email, then sleeps and resumes when a reply arrives (up to 7 days), updating issue confidence when done
7. **Live in the UI** — every task emits `pipeline_events` via Postgres NOTIFY → SSE; the Prism Stream dashboard shows each stage, its status, attempt number, and duration in real time; a retry in Render appears as a visible retry on screen
8. **Render dashboard beside PRISM** — during the demo, the Render task-run view is shown side-by-side with the Prism Stream, so judges can see both telling the same story
