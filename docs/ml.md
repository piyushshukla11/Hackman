# PRISM ML and Language Strategy

Principle: local, cheap, deterministic models do routine work. LLMs are used only for ambiguous cases, survey drafting and label OCR. Every model sits behind an interface so it can be swapped.

## 1. Model inventory

| Purpose | Default | Interface | Fallback |
| :-- | :-- | :-- | :-- |
| Sentence embeddings (dedup, feature mapping, clustering) | `intfloat/multilingual-e5-small` (384-d, about 100 languages incl. Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali), ONNX int8 for serving | `EmbeddingProvider.embed(texts, kind)` | Hosted embedding API |
| Language/script ID | fastText-style language ID plus Unicode script ranges | `LanguageDetector` | `langdetect`-style library |
| Romanised Indic / Hinglish detection | Lexicon hit rate of Indic function words in Latin script | `HinglishDetector` | LLM check on uncertain text |
| Translation to English | Sarvam translate (formal mode, auto source) | `Translator` | LLM translation, then keep original with penalty |
| Sentiment polarity (English-normalised sentence) | Full 7,500-word `vaderSentiment` analyzer augmented with Indian e-commerce & Hinglish dictionary (`sentiment_lexicon.yaml`) + negation rules + rating prior `(rating - 3) / 2`; optional compact Transformer head | `SentimentModel.score(sentence)` | Lexicon + negation scorer |
| Sarcasm/ambiguity first pass | Rule and feature scorer (see section 4) | `AmbiguityScorer` | n/a |
| Ambiguity second pass, survey drafting and summary, recommendation wording | Gemini (structured JSON output) | `LLMClient` | Rule-based result with lower confidence; category fallback questions |
| Label/serial text and damage from images | Gemini vision (or Tesseract for plain label OCR) | `ImageReader` | Skip, batch ladder drops to B2 |
| Statistics | scipy / statsmodels | n/a | n/a |

Note on e5: `intfloat/multilingual-e5-small` covers 100+ languages natively. It needs `query:` / `passage:` prefixes; we wrap this in `EmbeddingProvider` so reviews use `passage:` and anchors/custom features use `query:`. Cosine similarities from e5 are compressed (typically high, 0.70-0.92). Hence all similarity thresholds are **calibrated**, never copied from the old MiniLM values. Model weights are baked into Docker for instant startup.

## 2. Embedding use

| Use | Detail |
| :-- | :-- |
| Near-duplicate detection | pgvector HNSW nearest-neighbour lookup within same product; initial threshold 0.95 (calibrate); cross-language duplicates caught because the space is shared |
| Feature mapping | sentence vs anchor similarities; relative margin selection (within margin of top) plus calibrated floor; max 4 features per sentence |
| Graph edges | pairwise similarity within feature and polarity |
| Cluster consistency | mean pairwise similarity of cluster members |
| Caching | embeddings stored in `reviews.embedding`; anchors embedded once per taxonomy version |
| Batching | encode in batches (32 to 64) inside the worker; models loaded once per worker process |

## 3. Feature taxonomy & Company Custom Features

- **Company Custom Features (Max 15 per product):** Companies/tenants can define up to 15 custom features per product (e.g. "ear cushion comfort", "fizz", "strap durability"). Any word or phrase can be input.
  - Zero-shot matching: PRISM embeds each custom feature phrase using `multilingual-e5-small` (`query: <phrase>`) and caches it in `feature_taxonomies`.
  - Auto-anchor generation: Generates 2-3 synonym/anchor variations so matching accuracy is maximized without model re-training.
- **Category Seed Taxonomies:** Stored in `feature_taxonomies` per category: headphones, refrigerator, controller, monitor, plus a generic one (packaging, delivery, customer support, value for money, build quality).
- Anchors are phrases, not single words, and each feature has 3 to 6 anchors; similarity to a feature is the max over its anchors.
- **Stretch (not in core MVPs):** emerging feature discovery by clustering unmatched sentences and proposing new feature names for an admin to approve.

## 4. Sarcasm, mixed and vague handling

Two-step design: cheap signals everywhere, LLM only where signals fire.

**First-pass signals (per feature mention)**

| Signal | Rule | Weight (initial) |
| :-- | :-- | :-- |
| `rating_text_conflict` | rating at or above 4 and text polarity strongly negative, or rating at or below 2 and text strongly positive; conflict strength scales with distance (0.5-step ratings give finer gradation) | high |
| `mixed_polarity` | positive and negative cues both present, difference small | medium |
| `vague` | fewer than 4 content words in the feature sentence | low |
| `irony_markers` | "great, just great", "wow", "thanks a lot" style patterns, irony emoji, scare quotes | medium |
| `lang_tier` | low-resource language (tier 3) | adds uncertainty |
| `contrast_clause` | "but", "lekin", "aana" style contrast with opposing polarity | medium |

Combine into `ambiguity_score`. Below `t_low`: `none`. Between: heuristic label (`vague` or `mixed`). Above `t_high`: LLM second pass.

**LLM second pass (structured output)**

Input: masked English text, original snippet, rating, detected features, signals fired. Output JSON schema:

```json
{ "label": "sincere | sarcastic | mixed | unclear",
  "features": [{ "feature": "battery_life", "polarity": "neg|pos|neutral", "confidence": 0.0 }],
  "reason": "short" }
```

Results are stored with the signals so X-ray can display why. If `unclear` or the call fails, keep the heuristic and apply the multiplier.

**Confidence multipliers:** none 1.00, vague 0.85, mixed 0.70, sarcasm 0.55 (carried into issue confidence as the AmbiguityPenalty).

Rating-only reviews skip this step.

## 5. Language strategy (20+ Indian languages, code-mixed)

**Tiers**

| Tier | Languages (examples) | Handling |
| :-- | :-- | :-- |
| T1 | English, Hindi, Hinglish | Full pipeline, high trust in model outputs |
| T2 | Tamil, Telugu, Kannada, Malayalam, Bengali, Marathi, Gujarati, Punjabi | Translate + multilingual embeddings; moderate confidence discount |
| T3 | Odia, Assamese, Urdu, Konkani, other scheduled languages and romanised forms | Translate with fallback chain; more LLM second-pass usage; larger discount; flagged in UI |

**Low-resource tactics**
1. Shared multilingual embedding space so dedup and clustering work across languages without translation.
2. Translate-then-analyse for sentiment; keep original text for evidence and for embeddings.
3. Fallback chain: Sarvam → LLM translation → original text with `lang_tier_penalty`.
4. Per-language reporting in eval; the UI shows language alongside findings and never hides low accuracy.
5. Lexicons (negation, irony, safety) per language group, extendable as YAML.

**Code-mixing/Hinglish:** detect by Latin-script text with Indic function-word hits; send whole text to translation (Sarvam handles code-mixed input); keep emoji and punctuation intact.

## 6. Trust-related ML (non-LLM)

- **Template detection:** normalise text to a skeleton (numbers, product names replaced), cluster by skeleton hash plus embedding similarity; many authors using one skeleton → `TEMPLATE`.
- **Burst detection:** per product-channel-day counts with a rolling mean/std z-score; rating spikes via change in rating histogram (e.g. total variation distance to baseline).
- **Author reuse:** same author hash reviewing many products in a short time.
- **Promo patterns:** regex lexicon (multilingual), links, phone numbers, repeated emoji.
- All gates output reason codes; weights are config values.

## 7. Batch inference ML

- **OCR/vision:** extract candidate batch/serial strings from label photos, then match against the product's batch code regex (from `batches`/product config). Confidence from OCR confidence times pattern match.
- **Registry match:** date and warehouse lookup (pure rules).
- **Cohort fallback:** time-window and channel cohorts, always labelled approximate.
- Evaluate each rung separately (section 9).

## 8. Statistics used

| Need | Method |
| :-- | :-- |
| Difference in negative rate | Two-proportion z-test, Wilson intervals |
| Difference in ratings (0.5 steps, ordinal) | Mann-Whitney U with rank-biserial effect size |
| Many comparisons | Benjamini-Hochberg |
| Trend change | EWMA / CUSUM on weekly rates |
| Small samples | Minimum n gate (initial 20 per side); pooling across sibling batches/variants with shrinkage, labelled `pooled` |
| Confidence calibration | Reliability curve and expected calibration error (ECE) on seeded ground truth |

## 9. Evaluation harness (`seeds/` + `scripts/eval.py`)

**Dataset (generated with ground truth)**
- About 1,500 reviews, 4 products, 6 sites, 16 weeks; 20+ languages represented (heavier on Hindi, Hinglish, Tamil, Kannada, Bengali).
- Labelled injections: bot clusters, exact and near duplicates, templates, sarcastic and mixed reviews, rating-only entries, short reviews, serious complaints.
- Planted issues: a batch defect (start date known), a systemic issue, a channel-specific issue, a version change with real improvement.
- A simulated returns series for lead-time scoring.
- Generation: LLM-assisted with human spot checks; labels stored alongside text; a held-out portion used for calibration vs test.

**Metrics**

| Area | Metric |
| :-- | :-- |
| Trust | Precision/recall of spam and duplicate detection; rating-bias reduction with vs without trust weighting |
| Language | Feature-sentiment accuracy/F1 per language and tier |
| Sarcasm/ambiguity | F1 for sarcastic/mixed; LLM call rate |
| Feature mapping | Per-feature precision/recall; confusion matrix (to prove no "everything is battery") |
| Batch inference | Accuracy per ladder rung; accuracy with vs without explicit batch IDs |
| Detection | Batch-issue precision/recall; **detection lead time vs returns signal** (headline metric) |
| Classification | Confusion matrix of isolated / batch / systemic / channel_specific |
| Confidence | ECE and reliability curve; survey effect on calibration |
| Comparison | Version-impact detection (known improvement found, no false improvement on null) |
| Ops | Latency per stage, LLM calls per 100 reviews, cost estimate |

**Use in CI:** a small fixed subset runs on every push; thresholds floors (for example spam precision, batch recall) fail the build if breached.
**Use in demo:** an eval report page/PDF section generated from the latest `eval_runs` row.

## 10. Initial threshold table (all in `thresholds.yaml`, calibrate before use)

| Parameter | Initial |
| :-- | :-- |
| Min words for text | 2 |
| Near-duplicate similarity | 0.95 |
| Trust verdict cuts | clean at or above 0.70; suspicious 0.40 to 0.69; rejected below 0.40 |
| Feature margin / floor | margin 0.04; floor calibrated |
| Edge threshold | 0.45 |
| Top-k edges per node | 8 |
| Isolated size | below 3 |
| Batch rule | 4+ mentions, 70% one batch, at most 21 days, p below 0.01 |
| Systemic rule | 3+ batches or more than 6 weeks, 2+ channels |
| Channel-specific | 80% one channel |
| Confidence weights | 0.25 / 0.20 / 0.20 / 0.15 / 0.20 |
| Confidence levels | 0.75 act, 0.45 monitor |
| Min n for comparisons | 20 per side |
| Negative-rate spike alert | 0.60 with minimum sample |

## 11. Privacy in ML calls
- Mask PII before any external call (Sarvam, Gemini); mapping stays in memory in the task.
- Send the minimum text needed (the feature sentence plus context, not entire histories).
- Log LLM calls (purpose, tokens, latency, fallback used) without storing unmasked text.

## 12. Smart, Cost-Efficient Multimodal Processing (Images & Videos)

Principle: Avoid passing raw heavy video/image streams directly into multimodal LLMs. Extract lightweight cues first.

- **Audio Track First (Videos):** `ffmpeg` strips the audio track to 16kHz mono. Sarvam/Whisper STT converts spoken complaints to text in seconds. Captures >80% of video review signal at 90% lower compute cost.
- **Keyframe Extraction (Videos):** `ffmpeg` extracts up to 3 candidate frames using scene-change detection (`gt(scene,0.4)`) or equidistant timestamps (25%, 50%, 75%).
- **Image Pre-processing:** Scaled to 768px max dimension before ingestion.
- **Selective Vision Gating:** Candidate frames/images are only forwarded to Gemini Vision if:
  1. The customer review/audio contains visual failure keywords (`"cracked"`, `"smoke"`, `"burnt"`, `"shattered"`, `"bent"`, `"leak"`).
  2. Or serial/barcode OCR is required for batch inference ladder (B1).
  Otherwise, Vision LLM is skipped ($0 extra cost).

## 13. RAG-Based Diagnostic Survey Generation

Instead of naive ungrounded prompts, PRISM uses a compact RAG pipeline to generate diagnostic multiple-choice survey questions:
1. **Retrieval:**
   - Top 4 representative verbatim customer complaints from the identified issue cluster.
   - Product technical specifications from `products.specs` in the catalog (e.g. battery chemistry, operating temp, torque specs).
   - Dominant batch code and firmware release.
2. **Augmentation & Generation:**
   - Injects the retrieved context into Gemini structured JSON prompt.
   - Generates 3 hyper-targeted multiple-choice diagnostic questions to isolate engineering failure modes (e.g. isolating firmware freeze vs hardware cell degradation).
3. **Deterministic Fallback:** Category-level pre-calibrated diagnostic templates if LLM is unavailable or low-confidence.
