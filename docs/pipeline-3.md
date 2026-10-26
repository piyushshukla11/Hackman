# PRISM Pipeline

Stages P0 to P9 map onto the five layers. Every threshold named here lives in `thresholds.yaml` (values marked *initial* must be calibrated, see `ml.md`).

```
P0 Gateway ─► P1 Normalise ─► P2 Trust ─► P3 Understand ─► P4 Batch ─► P5 Graph ─► P6 Trends ─► P7 Compare ─► P8 Confidence ─► P9 Act
 (L1)           (L2)           (L2)         (L3)             (L3)        (L4)         (L4)         (L4)          (L4)            (L5)
```

## Core data rule: text and rating are separate

Each review has a **rating** (0.5-step stars) and optional **text**. They have separate statuses:
- `text_status`: `accepted | rejected_short | rejected_spam | rejected_dup | none`
- `rating_status`: `counted | downweighted | excluded`

A review whose text is rejected (for example fewer than 2 words) **keeps its rating** if it passes the bot gates. Rating-only submissions (widget star tap without text) are first-class (`kind: rating_only`).

---

## P0. Ingest gateway (L1)
- **In:** adapter pull, webhook push, widget, extension, file, email.
- **Do:** validate schema, map to the `RawReview` envelope, compute `idempotency_key`, store in `raw_reviews`, enqueue a `process_review` task.
- **Rating normalisation (per adapter):** map any scale to 0.5-step stars, 0.5 to 5.0. 10-point scale: `stars = round(x / 2 * 2) / 2` style rounding to nearest 0.5. Thumbs: up = 4.5, down = 1.5 (flagged `rating_derived=true`). Out-of-range or non-numeric rating: payload rejected to a dead-letter list with reason.
- **Idempotency key:** `sha256(tenant | source | source_review_id)`; if the source has no ID, `sha256(tenant | source | product | author_hash | reviewed_at | normalised_text)`. Duplicate key: no-op.
- **Out:** `raw_id`.

## P1. Normalise (L2)
- Script detection (Unicode ranges) and language ID (fastText-style model). Detect **romanised Indic / Hinglish**: Latin script plus lexicon hits of Hindi (and other) function words; label `hi-Latn` etc.
- English fast path: unicode normalise, whitespace, emoji kept as tokens (emoji are signals for sarcasm).
- Non-English or code-mixed: translate to English (Sarvam, formal mode) into `text_en`; keep `text_original`. On translation failure: LLM translation; on second failure keep original and mark `lang_tier_penalty`.
- PII masking applied to anything sent to external services.
- **Out:** `NormalisedReview(lang, script, text_original, text_en, emojis)`.

## P2. Trust cascade (L2)

A visible, ordered cascade. Each gate writes a row to `trust_gate_log` with `gate`, `verdict` (`pass | warn | fail`), `reason_code`, `score_delta`.

| Gate | Check | Effect |
| :-- | :-- | :-- |
| G1 Length | fewer than **2 words** after cleanup | `text_status=rejected_short`, reason `SHORT_TEXT`; **rating continues** |
| G2 Exact dupe | hash of normalised text already seen for same tenant/product | `rejected_dup`, reason `EXACT_DUP`; rating excluded if same author and same product |
| G3 Near-dupe | cosine similarity of multilingual embeddings above threshold (initial 0.95) against recent reviews of the same product, cross-language included | `rejected_dup`, reason `NEAR_DUP`; links to the original review |
| G4 Content heuristics | promo/seller shill patterns, links, phone numbers, repeated-emoji spam, generic one-liners ("good", "nice product") | `warn` or `fail`, reason `PROMO`, `LINK`, `GENERIC` |
| G5 Burst and coordination | per product-channel-day review count z-score; many reviews from one author hash; shared template cluster (same text skeleton across authors); rating spike far from the product's baseline in a short window | `warn` with reason `BURST`, `AUTHOR_REUSE`, `TEMPLATE`, `RATING_SPIKE` |
| G6 Provenance | verified-purchase flag, purchase date plausibility (review before purchase/delivery), source reliability | raises or lowers score |

**Trust score** (0 to 1): start at 1.0, subtract weighted penalties from `warn`/`fail` gates, add a small provenance bonus, clamp.

**Verdicts**
- `clean`: score at or above 0.70
- `suspicious`: 0.40 to 0.69 (quarantined from headline metrics, still stored and shown)
- `rejected`: below 0.40, or a hard fail (exact/near duplicate by same author, template match)

**Rating effect**
- `clean` → `rating_status=counted` (weight 1.0)
- `suspicious` → `downweighted` (weight = trust score)
- `rejected` for bot reasons → `excluded`
- `rejected_short` but otherwise clean → `counted`

Dashboards always display "with" and "without" quarantined reviews. Flagged reviews are kept, never silently deleted.

## P3. Understand (L3)

### 3a. Feature mapping
- Split into sentences. Embed each sentence (`multilingual-e5-small` with `passage:` prefix).
- For each sentence compute cosine similarity to company custom features (max 15 defined per product) and category anchors from `feature_taxonomy`. Select features using a **relative margin** (similarity within a margin of the top anchor) plus a calibrated floor, up to 4 per sentence.
- Merge with a keyword lexicon match (per language group) for features the embedding misses.
- Custom product features: companies can define up to 15 custom feature words/phrases per product (e.g. "ear cushion comfort", "fizz", "sugar level"), embedded zero-shot without model re-training.
- Category seed taxonomies: headphones, refrigerator, controller, monitor, plus seed generic.

### 3b. Polarity per feature
- Score the sentence that carries the feature with the full 7,500-word `vaderSentiment` analyzer augmented with the Indian e-commerce / Hinglish dictionary (`sentiment_lexicon.yaml`), adjusted by negation handling and the **rating prior**: converted rating `r' = (rating - 3) / 2` in [-1, 1]. Microsecond latency.
- A rating-only review contributes no feature polarity (no text), only rating metrics.

### 3c. Sarcasm and ambiguity gate (cheap first, LLM second)
Signals:
- `rating_text_conflict`: rating at or above 4 with strongly negative text, or at or below 2 with strongly positive text. The 0.5-step rating makes "4.5 + complaint" read as mixed, not sarcasm.
- `mixed_polarity`: both positive and negative cues close in strength.
- `vague`: fewer than 4 content words in the feature sentence.
- `irony_markers`: patterns like "great, just great", "wow", irony emoji, quoted praise.
- `lang_tier`: low-resource language raises the chance of misreading.

Outcome per feature mention: `ambiguity ∈ {none, vague, mixed, sarcasm}` with confidence multipliers **1.00 / 0.85 / 0.70 / 0.55**.

If any signal fires above threshold, call the **LLM second pass** (Gemini structured output, JSON schema, masked text). Returns `label ∈ {sincere, sarcastic, mixed, unclear}` plus corrected per-feature polarity. If the LLM is unavailable or still `unclear`, keep the heuristic result, apply the multiplier, and set `needs_second_opinion=false` (no human queue in this build). Ambiguous mentions still count, with reduced weight, and are labelled in X-ray.

### 3d. Serious-complaint branch (parallel, does not stop the main flow)
- Multilingual safety lexicon plus semantic match to safety anchors (fire, smoke, burn, shock, explosion, overheating, injury, rash, choking, leak). Image/OCR hints later.
- Score `severity` (harm potential) and `urgency` (recency, repetition across authors). Above threshold → insert into `serious_complaints`, emit `serious.new`, optional Slack webhook.
- The review also continues through the normal pipeline.
- `suspicious` reviews with safety keywords are still surfaced in the serious queue, flagged as unverified.

**Out:** `ReviewAnalysis(features[], polarity, ambiguity, mult, serious?)`.

## P4. Batch inference (L3)

Ladder, first rung that yields a result wins; each records `batch_method` and `batch_conf`.

| Rung | Signal | Conf |
| :-- | :-- | :-- |
| B0 Explicit | batch code from widget QR, CSV, extension, or review metadata | 1.00 |
| B1 Label text | batch/serial text read from images (OCR) matched against the batch code pattern of the product | 0.85 |
| B2 Registry match | purchase or dispatch date plus warehouse/seller matched to `batches` ship windows | 0.70 |
| B3 Cohort | product × channel × purchase/delivery fortnight (a pseudo-batch) | 0.50 |
| B4 Review-time cohort | product × channel × review fortnight (only when no purchase date) | 0.30 |

- Reviews inferred below B2 are labelled "approximate batch" in the UI, and issues built mostly from low rungs are capped in confidence through the evidence-strength term (P8).
- Batches map to `product_versions`, so every review also gets a `version_id`.
- Cold start: if a batch has fewer than N reviews, results are pooled with sibling batches of the same version and labelled `pooled`.

## P5. Issue graph and classification (L4)

**Nodes** are feature mentions (one review can appear in several features). **Edges** connect mentions of the same product, same feature and same polarity:

```
weight = 0.40 * semantic_similarity
       + 0.25 * time_proximity        (1 - days_apart / 28, floored at 0)
       + 0.25 * batch_affinity        (1 same batch, 0.6 same version, 0.3 same cohort, else 0)
       + 0.10 * symptom_overlap       (shared symptom keywords/phrases)
edge if weight >= 0.45   (initial); keep top-k (8) per node
```

Clusters are connected components over negative-polarity edges (and separately positive, labelled `praise`). Only trusted mentions (trust at or above 0.40) enter; suspicious ones are included at reduced weight and counted separately.

**Classification** (using rolling windows against a per-product baseline, not raw counts):
- `isolated`: fewer than 3 mentions
- `batch`: 4 or more mentions, at least 70% (confidence-weighted) in one batch, duration at most 21 days, and negative rate lift over baseline significant (two-proportion test, p below 0.01)
- `systemic`: spans 3 or more batches or more than 6 weeks, across at least 2 channels, persists
- `channel_specific`: at least 80% of mentions from one channel or seller (platform or seller problem, not product)
- `praise`: positive cluster

Each issue stores affected batches, channels, versions, languages, first/last seen and member list.

## P6. Trends and rollups (L4)
- Maintain `metric_rollups` per `(product, version, batch, channel, feature, week)`: review count, negative/positive counts, **trust-weighted rating sum**, and **all-reviews rating sum** (for with/without views). All comparisons read from here.
- Rolling windows: weekly and "last 50 reviews". Negative rate gets a Wilson interval.
- Change detection: EWMA/CUSUM on weekly negative rate; patterns:
  - `batch_spike`: sharp rise concentrated in one window that decays
  - `design_creep`: 3 or more consecutive weeks of growth
- Rating series: trusted weighted mean vs all-reviews mean, so a flat 4.4 average and a rising complaint rate can be shown side by side.
- Output feeds alerts (negative rate above 0.60 with minimum sample), debounced to once per 7 days per product-feature.

## P7. Comparison engine (L4)

One function: `compare(lens, A, B, metric)`. Lenses:

| Lens | A vs B |
| :-- | :-- |
| `product` | product X vs product Y (same category) |
| `time` | window 1 vs window 2, or week-over-week |
| `batch` | batch vs baseline of other batches |
| `channel` | channel vs other channels for the same product |
| `version` | before vs after a modification (default 4 weeks each side) |

Metrics: trust-weighted mean rating, negative rate per feature, health score.
Statistics: proportions → two-proportion z-test with Wilson CI; ratings (ordinal, 0.5 steps) → Mann-Whitney U with effect size; scanning many groups → Benjamini-Hochberg correction. Minimum n (initial 20 per side) else verdict `insufficient_data`.
Output: delta, CI, p-value, n each side, verdict (`better | worse | no_change | insufficient_data`), top contributing features.

**Version impact:** a `modification` marks the effective date and optional target feature/issue. The engine reports whether the target feature's negative rate and the rating changed after the modification, using batches mapped to the new version.

**Health score (0-100):** `0.35 * rating_component + 0.45 * feature_sentiment_component + 0.20 * (1 - open_issue_penalty)`, where `rating_component = (trusted_mean - 1) / 4`, feature component is mention-weighted positive share, and the penalty is severity-weighted open issues. Weights are in config.

## P8. Confidence (L4)

```
base = 0.25*Frequency + 0.20*Density + 0.20*Consistency + 0.15*Temporal + 0.20*Evidence
confidence = clamp( base * AmbiguityPenalty + CoherenceBonus + SurveyDelta , 0, 1 )
```

| Term | Meaning |
| :-- | :-- |
| Frequency | affected share and lift over baseline, saturating |
| Density | cluster size relative to saturation point (initial 8) |
| Consistency | mean pairwise semantic similarity inside the cluster |
| Temporal | fit to `batch_spike` or `design_creep` shape |
| Evidence | mean trust score × batch-inference confidence × media evidence factor |
| AmbiguityPenalty | mean ambiguity multiplier over members |
| CoherenceBonus | +0.05 if more than half of pairs are strongly similar |
| SurveyDelta | from verification replies (P9), capped at ±0.20 |

Levels: at or above 0.75 **Act**, 0.45 to 0.74 **Monitor**, below 0.45 **Gather data**.
Severity: high (negative cluster, 8 or more mentions), medium (4+), low (else). Rank = confidence × severity weight (3/2/1).
The full breakdown is stored in `confidence_parts` so the UI can draw the waterfall and drill into reviews behind each bar.
Recommendations come from a (feature × issue_type) action matrix in config; LLM wording is optional and always grounded in the stored evidence.

## P9. Act (L5)

### Verification survey (long-running task)
1. **Trigger:** issue confidence in the Monitor/Gather band, or a serious complaint, or manual trigger.
2. **Targets:** affected reviewers who gave consent and an email (widget/extension/CSV capture it). No consent, no survey.
3. **Draft:** RAG-grounded generator retrieves top 4 cluster customer verbatims + product technical specs from catalog (`products.specs`) + batch/firmware details; Gemini structured JSON prompt drafts 3 targeted diagnostic multiple-choice questions to isolate root cause; category-based fallback questions if LLM fails.
4. **Send:** email module; signed expiring link to the survey page.
5. **Wait:** the long-running task sleeps until a reply or expiry (default 7 days), with reminder at day 3.
6. **Ingest reply:** LLM writes a 2-sentence summary; a rule maps answers to confirm/deny signals; `SurveyDelta` updates the issue confidence (for example 0.62 → 0.81) and emits `survey.reply`.

### Other actions
- Serious alerts: email and optional Slack webhook.
- Spike alerts to `alerts` and SSE.
- Weekly digest per role (cron).
- Company report PDF on demand (see below).

### Company report (PDF)
Built in the backend from rollups and issues: executive summary, health score and trust note, product comparison, channel performance per product, batch and version impact, top issues with evidence counts, serious complaints, recommendations. HTML template → PDF.

---

## Render Workflows mapping

| Task | Trigger | Parallelism | Retries |
| :-- | :-- | :-- | :-- |
| `ingest_pull(source)` | cron per source / webhook | one per source | 3, backoff |
| `process_review(raw_id)` | enqueued by gateway | fan-out per review (chunks of N) | 3, backoff |
| ↳ `normalise`, `trust`, `understand`, `batch_infer` | subtasks | sequential per review | per stage |
| `rebuild_product(product_id)` | after fan-out completes | one per product | 3 |
| ↳ `graph`, `rollups`, `compare_cache`, `score_issues` | subtasks | sequential | per stage |
| `notify(product_id)` | after score | one | 3 |
| `survey_loop(issue_id)` | issue band or manual | long-running, one per survey | resume-safe |
| `trend_scan` | cron (hourly or daily) | per product | 2 |
| `weekly_digest` | cron (Mon 09:00 IST) | per tenant and role | 3 |
| `source_health` | cron (every 10 min) | per source | 1 |
| `build_report(product_id)` | API request | one | 2 |

Each task emits `review.stage` events (stage, status, attempt, duration) so the UI and the Render dashboard tell the same story. Confirm Workflows SDK specifics (scheduling, long-running wait, fan-out API) in Render docs before implementing.

## Versioning and reprocessing
Each stage has a `STAGE_VERSION`. `reviews.stage_versions` records what ran. Bumping a version (new model, new thresholds) triggers `reprocess(product_id, from_stage)` which re-runs only that stage and later stages.

## Worked example (the demo story)
Day 0 to 4: 6 packaging complaints arrive in Hindi, Hinglish and English across 3 channels. Three have ratings of 4.0 to 4.5 with damage text (mixed, not sarcasm). All have dispatch dates in the same 9-day window from warehouse W2 → B2 batch match. P5 forms a negative `packaging` cluster, size 6, 85% in batch B-0716, 3 channels, 9 days → `batch`. P8 confidence 0.68 (Monitor) because only 2 of 6 have images with label text. P9 sends surveys to the 4 consenting reviewers; 3 confirm "box crushed on arrival, same courier". Confidence rises to 0.84 (Act). The all-reviews rating still reads 4.4; returns spike on day 19; PRISM flagged on day 4.
