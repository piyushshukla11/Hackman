# PRISM Features and Decisions

## 1. Feature list by module (with MVP number)

| # | Module | Feature | MVP |
| :-- | :-- | :-- | :-- |
| F1 | Ingest | Gateway, `RawReview` envelope, idempotency, rating normalisation (0.5 step) | 1 |
| F2 | Ingest | 6 placeholder simulated sites with different API shapes + adapter interface | 1 |
| F3 | Ingest | CSV/JSON upload with mapping profiles | 1 |
| F4 | Clean | Language/script detection, Hinglish detection, translation (Sarvam) | 2 |
| F5 | Clean | Trust cascade (G1 to G6), trust score, reason codes, quarantine instead of delete | 2 |
| F6 | Clean | Text/rating split: short text rejected (fewer than 2 words), rating still counted | 2 |
| F7 | Understand | Multilingual feature mapping with per-category taxonomy | 3 |
| F8 | Understand | Sentiment per feature, rating prior, negation | 3 |
| F9 | Understand | Sarcasm/mixed/vague detection with LLM second pass, confidence multipliers | 3 |
| F10 | Understand | Serious-complaint scoring and separate queue, Slack webhook | 3 |
| F11 | Understand | Batch inference ladder B0 to B4 with confidence labels, cold-start pooling | 4 |
| F12 | Diagnose | Issue graph; classes isolated / batch / systemic / channel_specific / praise | 4 |
| F13 | Diagnose | Rolling-window trends, change detection, `batch_spike`, `design_creep` | 4 |
| F14 | Diagnose | Comparison engine: product, time, batch, channel, version lenses with significance | 5 |
| F15 | Diagnose | Product versions and modifications, before/after impact verdict | 5 |
| F16 | Diagnose | Confidence breakdown (waterfall), health score, evidence quality | 5 |
| F17 | Act | Verification surveys (LLM-drafted), long-running loop, confidence update | 6 |
| F18 | Act | Email module: templates, outbox, delivery status, consent, unsubscribe, API | 6 |
| F19 | Capture | Widget (rating-first, batch code via QR, consented email) | 7 |
| F20 | Capture | Chrome extension with site profiles, own-listing capture, verdict overlay | 7 |
| F21 | Ops | Source health monitor | 8 |
| F22 | Ops | Eval harness with benchmark report and CI smoke test | 8 |
| F23 | Act | Company report PDF | 8 |
| F24 | UI | Judge mode (real pipeline replay on seed data) | 8 |
| F25 | UI | Prism Stream, X-ray, forensic timeline, waterfall, survey thread, compare view | 3 to 8 |
| F26 | Platform | Auth, tenancy, roles, API keys, CI/CD, Render Blueprint | 1 and 8 |

Role outputs (QA, ops, support, marketing, leadership) are lenses and digest templates over the same data, not separate pipelines.

## 2. Keep / Fix / Cut / Add (versus old project)

**Keep:** 7-stage shape, trust gate concepts, edge-weight idea, cluster classification idea, confidence formula terms, Gemini survey drafting with fallbacks, Sarvam translation, ambiguity multipliers (1.0/0.85/0.70/0.55).

**Fix:** English-only embeddings → multilingual; word-list sentiment → model plus rating prior plus LLM second pass; static 7 features → per-category taxonomy; fixed "3 weeks, 4 nodes" rule → baseline and significance based; SQLite → Postgres + pgvector; in-memory cache → rollups table; Socket.io → SSE; hardcoded localhost → config; hardcoded credentials → seeded users; hardcoded catalog → catalog tables; flagged reviews dropped from ratings → trust-weighted rating.

**Cut:** Vercel deployment, SQLite, Socket.io, Redis, mock fallbacks in UI, decorative WebGL backgrounds, duplicated product catalogs, html-pdf-node, four separate near-identical storefront mocks (replaced by 6 distinct placeholder sites that each exercise an adapter), human review queue (not in this build), evidence pack export, recommendation-closure tracking.

**Add:** batch inference, serious-complaint queue, rating as signal, comparison engine, versions/modifications, widget and extension, source health, eval harness, tenancy, PII masking, role lenses, Judge mode, Render Workflows.

## 3. Decision log

| ID | Decision | Why | Alternative rejected |
| :-- | :-- | :-- | :-- |
| D1 | Python for backend and workers | ML libraries, one language for pipeline, user preference | Node (ONNX embeddings heavier, weaker ML tooling) |
| D2 | Render Workflows for pipeline | Sponsor track; durable tasks, retries, fan-out are real needs | Celery/Redis (extra infra, no sponsor value) |
| D3 | Single Postgres with pgvector | One datastore for rows, vectors and rollups; simpler ops | Separate vector DB (extra moving part) |
| D4 | Multilingual embeddings (multilingual-e5-small, 384-d) | Covers Tamil, Kannada, Bengali and others the old English MiniLM could not | LaBSE (768-d, heavier), English MiniLM |
| D5 | Translate-then-analyse for non-English, keep original | Sentiment models are strongest in English; originals retained for evidence | Native per-language sentiment models (too many to maintain) |
| D6 | Local models first, LLM only for ambiguous cases, surveys, OCR | Cost, latency, privacy, determinism | LLM for everything |
| D7 | Rating is separate from text; short text rejected, rating kept | A bare rating is still evidence and moves averages; bots can too, so it is trust-checked | Drop whole review when text is rejected |
| D8 | Min text length is 2 words | Single-word reviews carry no feature signal | 3 words (old) |
| D9 | Quarantine, do not delete | Judges and users can audit trust decisions | Hard delete |
| D10 | Trust is a score with reason codes, shown beside metrics, with and without quarantined views | Makes trust visible and defensible | Binary spam flag |
| D11 | No human review queue (this build) | Keeps scope clean; ambiguity handled by LLM second pass plus confidence discount | Human-in-the-loop (cut for now, easy to add later) |
| D12 | Nodes are feature mentions, not whole reviews | A review with two features belongs to two issues | One node per review (old) |
| D13 | Classification relative to baseline with significance tests | Raw counts mislead for popular vs niche products | Fixed count and week thresholds |
| D14 | Batch inference as a ladder with explicit confidence | Batch IDs are usually missing; honesty about approximation | Require batch ID (unrealistic) |
| D15 | One comparison engine over a rollups table | Five lenses without five pipelines | Per-lens custom queries |
| D16 | Versions/modifications entity | Answers "did the fix work?" and connects batches to design changes | Free-text notes |
| D17 | SSE with Postgres LISTEN/NOTIFY | Works with multiple API instances, no Redis, simple | Socket.io (stateful), Redis pub/sub |
| D18 | Widget and extension both real | Covers sources with no API; extension also gives context for batch inference and a verdict overlay | Widget only |
| D19 | Docker runtime on Render | ML deps and PDF libraries | Native Python runtime |
| D20 | Backend generates reports and digests | Outputs are consumable without the UI | UI-rendered reports |
| D21 | Surveys only with consent | Privacy and DPDP-aware design | Email every flagged reviewer |
| D22 | Video/audio not processed in this build (a provided transcript is accepted) | Scope control; images (label OCR, damage) give the multimodal story | Full audio/video pipeline |
| D23 | Thresholds in config, calibrated by eval | Embedding similarity scales differ by model; avoid magic numbers | Hardcoded values |

## 4. Risks and mitigations

| Risk | Mitigation |
| :-- | :-- |
| Workflows SDK details differ from assumptions | Thin adapter around plain Python task functions; read docs first; fall back to API-triggered background jobs if a feature is missing |
| Worker memory too small for models | Quantised ONNX model, or switch `EmbeddingProvider` to a hosted API |
| Low-resource language quality | Language tiers, translation fallback chain, confidence discount, per-language eval numbers reported honestly |
| Thresholds wrong for e5 similarity scale | Calibration script on labelled seed data before demo |
| Extension scope creep | One or two site profiles only, profile-driven design |
| Demo depends on LLM/translation APIs | Cached outputs for the seeded set and rule-based fallbacks, clearly labelled as fallbacks |
| Seeded data looks fake | Generate with ground-truth labels, varied languages and noise; show eval metrics next to it |

## 5. Open items
- Names and branding of the 6 simulated sites (placeholders for now).
- Which real review APIs to integrate after the hackathon core (to be researched).
- Final choice of email provider.
- Confirm Render Workflows features: scheduling, long-running waits, fan-out limits.
- Returns series for lead-time scoring is simulated; label it as such in the UI.
