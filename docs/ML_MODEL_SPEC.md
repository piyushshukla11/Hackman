# PRISM ML Intelligence Model Specification & Operating Manual

> **Document Status**: Living Architectural & Operational Ground Truth  
> **Target Package**: `ml_service/` (PRISM Advanced ML Engine)  
> **Last Updated**: October 2026  
> **Engine Version**: 2.0.0  

---

## 1. Executive Overview & System Architecture

The PRISM ML Service is a forensic diagnostic engine purpose-built for multi-channel, multilingual customer review intelligence. Unlike standard sentiment classifiers that assign a single positive/negative label to an entire review, PRISM executes a multi-stage, explainable pipeline designed to pinpoint root causes, isolate hardware batch defects, protect against review manipulation, and prioritize serious product safety hazards.

```
                           [ Raw Customer Review ]
                                      │
                                      ▼
                        [ Stage 1: Normalization ]
                     (Script ID, Hinglish, PII Masking)
                                      │
                  ┌───────────────────┴───────────────────┐
                  ▼                                       ▼
       [ Stage 2: Trust Cascade ]             [ Parallel: Safety Detector ]
    (G1-G6: Spam, Bots, Duplicates)         (Fire, Shock, Burns, Explosions)
                  │                                       │
                  ▼                                       ▼
       [ Stage 3: Feature Extraction ]           [ Instant Hazard Alert ]
   (Clauses, Taxonomy, Polarity Prior)
                  │
                  ▼
       [ Sarcasm & Ambiguity Check ]
      (Rating-Text Conflict, Gemini)
                  │
                  ▼
       [ Stage 4: Batch Inference ]
         (B0-B4 Inference Ladder)
                  │
                  ▼
       [ Stage 5: Issue Graph Engine ]
    (BFS Connected Components, Hypothesis Test)
                  │
                  ▼
       [ Stage 6: Confidence Waterfall ]
          (5-Term Multi-Factor Formula)
                  │
         ┌────────┴────────┐
         ▼                 ▼
[ Stage 7: Comparison ]  [ Stage 8: Diagnostic Surveys ]
 (5 Statistical Lenses)   (Gemini Dynamic Follow-Up)
```

---

## 2. Core Components Breakdown

### 2.1 Language & Script Normalizer (`models/language.py`)
- **Script Identification**: Direct Unicode script range mapping across 9 Indian scripts (Devanagari, Tamil, Telugu, Kannada, Malayalam, Bengali, Gurmukhi, Gujarati, Odia) plus Latin.
- **Hinglish Classifier (`hi-Latn`)**: Detects Latin-transliterated Hindi/Urdu using a 120-word phonetic frequency dictionary with script checking.
- **PII Masking**: Scans and sanitizes Personally Identifiable Information prior to model inference or LLM processing:
  - Spaced and prefixed Indian phone numbers (`+91`, `0`, 10-digit formats).
  - Extended TLD email addresses (`user@domain.museum`, `a.b+tag@example.com`).
  - Standard e-commerce order identifiers (`OD-123456`, `ORD#998877`).
- **Emoji Preservation**: Extracts and preserves Unicode emojis for sentiment polarity and sarcasm detection.
- **Translation Fallback**: Integrated with Sarvam API and Google Gemini 2.5 Flash for Tier-2 and Tier-3 low-resource languages, with deterministic rule-based pass-through when APIs are offline.

### 2.2 Multilingual Embeddings (`models/embeddings.py`)
- **Core Model**: `intfloat/multilingual-e5-small` (384-dimensional dense representations, PyTorch CPU optimized).
- **Asymmetric Prefixing**:
  - `query: ` prefixed to search terms, taxonomies, and clustering anchors.
  - `passage: ` prefixed to customer reviews, sentences, and clauses.
- **L2 Normalization**: All vectors are L2-normalized ($||\mathbf{v}||_2 = 1.0$), ensuring cosine similarity is directly computed via vector dot product.
- **Taxonomy Anchor Precomputation**: Precomputes and caches dense vectors for all category attributes at initialization time to achieve millisecond inference latency.

### 2.3 G1–G6 Trust Cascade (`models/trust.py`)
Evaluates review authenticity through 6 sequential gates and emits **decoupled statuses**:
1. **G1 Length & Content Check**: Reviews under 3 words or 15 characters are tagged `rejected_short`.
2. **G2 Exact Duplicate Fingerprint**: SHA-256 hash collision against historical corpus yields `rejected_dup`.
3. **G3 Promo & Link Filter**: Detects external URLs, referral codes, affiliate links, and shill phrases (`100% genuine`, `click here`).
4. **G4 Dense Semantic Near-Duplicate**: Cosine similarity $\ge 0.92$ against recent author reviews yields `rejected_burst`.
5. **G5 Burst Anomaly Gate**: Poisson / z-score deviation in daily submission velocity ($\text{z-score} > 3.0$).
6. **G6 Account Velocity Gate**: High frequency reviews from fresh, unverified accounts downweight trust.

#### Rating vs Text Status Invariant & Bounded Trust
- **Clean Reviews**: `text_status = 'clean'`, `rating_status = 'counted'`.
- **Short Clean Reviews** (e.g. `"Good"` or `"Awesome"`): `text_status = 'rejected_short'` (omitted from NLP/topic modeling to prevent noise), but **`rating_status = 'counted'`** (preserved in product star ratings).
- **Hard Fraud / Bots / Collusion**: `text_status = 'rejected_*'`, **`rating_status = 'excluded'`** (dropped completely from product rating calculations).
- **Verified Purchase**: Grants calibrated $+0.15$ trust boost, but **CANNOT** override G2 duplicates, G3 spam, or bot templates. It is not treated as proof of truth.
- **Explainability & Boundedness**: All trust scores are strictly bounded in $[0.0, 1.0]$. Deductions are explainable via explicit audit tags, and penalties are capped so no single weak signal can dominate the verdict.

### 2.4 Feature Extraction & Dual Sentiment Engine (`models/features.py`)
- **Review-Level vs Feature-Level Sentiment**:
  - *Review-Level Sentiment*: Evaluates the overall customer review independently from extracted features. Treats star ratings as weak calibrating priors ($0.15$ weight), not ground truth.
  - *Feature-Level Sentiment*: Granular polarity mapped to specific extracted components (`positive`, `negative`, `neutral`).
- **Feature Deduplication & Consolidation**: Consolidates multiple occurrences of the same feature within a single review into a single canonical record to prevent artificial feature count inflation.
- **Strict Domain Separation**: Distinctly separates packaging, delivery, customer support, and product quality.
- **Other/Unknown Fallback**: Evaluative sentiment clauses that do not match specific hardware features are mapped to an `other/unknown` category rather than discarded.
- **Clause-Level Contrast Splitting**: Clauses separated by contrast conjunctions (`, but`, `, however`, `;`, `lekin`) are evaluated independently.
- **Litotes & Negation Window**: Evaluates a 3-token window preceding sentiment words (`negation_window = 3`). Negated negative complaints (e.g. `"not bad"`, `"not terrible"`) yield mild neutral sentiment ($+0.10$), never extreme positive scores.

### 2.5 Sarcasm & Ambiguity Engine (`models/ambiguity.py`)
Multi-class disentanglement system that separates true rhetorical sarcasm from other complex linguistic phenomena:
- **Taxonomy of Ambiguity Verdicts**:
  - `sarcasm`: Genuine rhetorical irony with sneer cues, superlative praise paired with sudden failure descriptions, or explicit irony emojis.
  - `sincere`: Direct critical feedback and complaints (e.g. `"The design does not let water through"` or `"High quality parts do not break this fast"`). Never misclassified as sarcasm.
  - `mixed`: Contradictory praise and complaints across different features.
  - `rating_mismatch`: Star rating diverges from review text without rhetorical sarcasm (e.g., 5.0★ rating with a sincere bug report).
  - `vague`: Insufficient context to determine sentiment polarity.
  - `uncertain`: Weak evidence or ambiguous cues where definitive classification is unjustified.
- **Evidence Reporting**: Every prediction includes structured `evidence` and `explanation` audit fields.

### 2.6 Serious Complaint Safety Hazard Detector (`models/serious.py`)
Operates as an asynchronous parallel gate scanning for high-liability safety risks:
- **Actual Hazard Classes**:
  - `fire_explosion`: Active flames, combustion, smoke, explosions, battery swelling.
  - `electrical_shock`: Electric shocks, sparks, short circuits, exposed live wires.
  - `thermal_burn`: Blistered skin, third-degree burns, dangerous overheating.
  - `physical_injury`: Deep cuts, lacerations, severed parts, puncture wounds, stitches.
  - `chemical_hazard`: Corrosive battery acid, toxic chemical leaks, noxious fumes.
- **Strict Ordinary Defect Exclusion**: Everyday defects such as water leaks, melting ice cubes, noisy motors, compressor hums, slow cooling, or poor performance are explicitly excluded and never flagged as safety hazards.
- **Slang Immunity**: Slang praise like `"This new color is fire 🔥"`, `"smoking hot deal"`, or `"had a blast"` is sanitized before regex scanning.
- **Multi-Token Negation Scope**: Negated statements (e.g. `"No electric shock or sparks occurred"`) are scanned across a wide scope window and discarded.
- **Hypothetical & Quoted Warnings**: Hypothetical scenarios (e.g. `"Could have burned my house down"`) and quoted manual warnings return `verdict: "uncertain"` with `alert_required: False` and supporting evidence.
- **Unverified Reporter Rule**: If an active hazard is reported by a reviewer flagged as `suspicious`, the alert is still generated immediately with `unverified: true` so engineering can audit without delay.

### 2.7 5-Rung Batch Inference Ladder (`models/batch.py`)
Assigns customer complaints to manufacturing batches:
| Rung | Method | Confidence | Criteria |
| :--- | :--- | :---: | :--- |
| **B0** | Explicit Code | **1.00** | Explicit valid code on review or invoice (`B-0716`) |
| **B1** | Label OCR | **0.85** | Batch regex extracted from uploaded photo label |
| **B2** | Registry Match | **0.70** | Dispatch/purchase date falls within warehouse shipping window |
| **B3** | Purchase Cohort | **0.50** | Channel $\times$ Purchase Fortnight (`COHORT_AMAZON_2026_07_FN1`) |
| **B4** | Review Cohort | **0.30** | Channel $\times$ Review Fortnight proxy |

### 2.8 Feature-Level Issue Graph (`models/graph.py`)
- **Node Definition**: Individual extracted negative feature mentions.
- **Edge Creation Rules**: An edge is formed between mention $A$ and mention $B$ if and only if:
  1. $\text{Feature}(A) == \text{Feature}(B)$ (same attribute).
  2. $\text{Polarity}(A) == \text{Polarity}(B) == \text{negative}$.
  3. Dense cosine similarity $\ge 0.82$.
- **Graph Clustering**: Breadth-First Search (BFS) connected components.
- **Issue Type Classification**:
  - `isolated`: Cluster size $< 4$ mentions.
  - `batch`: Cluster size $\ge 4$, dominant batch proportion $\ge 70\%$, review span $\le 21$ days, mean reviewer trust $\ge 0.40$, and two-proportion hypothesis test vs product baseline $p < 0.01$.
  - `systemic`: High volume defect spanning multiple batches or long duration.
  - `wear_and_tear`: Defect emergence delayed past 90 days of ownership.

### 2.9 5-Term Confidence Waterfall (`models/confidence.py`)
Final defect confidence score is computed via a 5-term calibrated breakdown bounded strictly in $[0.0, 1.0]$:
$$\text{Base Confidence} = 0.25 F + 0.20 D + 0.20 C + 0.15 T + 0.20 E$$
Where:
- $F$ (Frequency): $\min(1.0, \text{size} / 20.0)$
- $D$ (Duration): Concentration penalty if mentions span beyond 30 days.
- $C$ (Batch/Cohort Concentration): Dominance ratio of leading batch.
- $T$ (Mean Reviewer Trust): Average trust score of contributing reviewers.
- $E$ (Evidence Quality): Weighted proportion of explicit B0/B1 batch evidence.

**Modifiers**:
- Ambiguity Multiplier ($0.60$ to $0.85$) applied for sarcastic or mixed reviews.
- Baseline Coherence Bonus ($+0.05$) when cluster defect rate significantly exceeds historical product rate.
- Empty cluster guard: Cluster size $0 \implies \text{Confidence} = 0.0$.

### 2.10 5-Lens Statistical Comparison Engine (`models/comparison.py`)
Audits differences across 5 lenses:
1. `product`: Compares defect rates between competing products.
2. `time`: Detects temporal spikes across 30-day windows.
3. `batch`: Compares defect frequencies across production batches.
4. `channel`: Evaluates platform-specific variations (Amazon vs Flipkart vs Direct).
5. `version`: Validates engineering revisions (v1.0 vs v1.1).

- **Statistical Rigor**: Uses Mann-Whitney U test for continuous star ratings, two-proportion z-tests for defect percentages, Wilson score intervals for small sample bounds, and Product Health Score ($0 - 100$).
- **Defensive Data Handling**: Samples with $N < 10$ or zero denominators safely return `insufficient_data` without NaN or division errors.

### 2.11 Adaptive Verification Survey Engine (`models/survey.py`)
- **Targeted Drafting**: Generates focused diagnostic follow-up questions for users who experienced ambiguous issues (e.g. clarifying whether audio dropouts occur on Bluetooth or wired mode).
- **Ingestion & Adjustment**: Answers adjust the issue cluster confidence via calibrated delta:
  $$\Delta = \frac{N_{\text{confirm}} - N_{\text{deny}}}{N_{\text{total}}} \times 0.15$$
- Unknown question IDs are ignored, and adjusted confidence is strictly clamped to $[0.0, 1.0]$.

---

## 3. Mathematical & Algorithmic Ground Truths (Invariants)

To ensure consistency across updates, any modification to the ML model must preserve the following **10 Invariants**:

| ID | Invariant | Description |
| :--- | :--- | :--- |
| **INV-01** | **Spam Rating Exclusion** | Reviews failing G2 (exact duplicate), G3 (promo link), or G4 (burst coordinate) must set `rating_status = 'excluded'`. |
| **INV-02** | **Short Review Decoupling** | Clean reviews under 3 words must set `text_status = 'rejected_short'` (excluded from NLP) but preserve `rating_status = 'counted'`. |
| **INV-03** | **Verified Purchase Limit** | Verified purchase status ($+0.15$) cannot redeem hard spam, duplicate hashes, or bot templates. |
| **INV-04** | **Clause Polarity Isolation** | Opposing clauses separated by contrast conjunctions (`bass muddy, but vocals clear`) must be extracted as separate features. |
| **INV-05** | **Litotes Neutrality** | Negated complaints (`not bad`, `battery is not terrible`) must have sentiment score $< 0.50$ (mild neutral, never confident positive). |
| **INV-06** | **Safety Negation & Slang Filter** | Slang phrases (`color is fire 🔥`) and negated hazards (`did not catch fire`) must never trigger safety alarms. |
| **INV-07** | **Batch Cluster Minimum Size** | Clusters with fewer than 4 mentions cannot be diagnosed as `batch` defects (must fall back to `isolated`). |
| **INV-08** | **Statistical Significance Gate** | Clusters with reviewer trust $< 0.40$ or $p \ge 0.01$ against product baseline defect rate must not be diagnosed as batch defects. |
| **INV-09** | **Zero Denominator Protection** | Comparison metrics on zero sample sizes or zero counts must return `insufficient_data` without exceptions. |
| **INV-10** | **Confidence Boundedness** | Final confidence scores, survey deltas, and trust scores must remain strictly bounded in $[0.0, 1.0]$. Empty clusters must yield $0.0$. |

---

## 4. API Endpoints Reference

All endpoints are hosted on the FastAPI microservice (`ml_service/main.py`) at port `8001`:

| Method | Endpoint | Request Body Schema | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/ml/health` | None | Returns service health, active models, vector dimensions |
| `POST` | `/ml/normalize` | `{"text": str}` | Script ID, Hinglish detection, and PII masking |
| `POST` | `/ml/trust` | `{"review_text": str, "verified_purchase": bool, ...}` | G1–G6 trust evaluation and decoupled rating status |
| `POST` | `/ml/extract` | `{"text": str, "category": str, "rating": float}` | Feature extraction, polarity prior, sarcasm check |
| `POST` | `/ml/batch-infer` | `{"explicit_batch_code": str, "dispatch_date": str, ...}` | 5-rung batch inference ladder (B0 to B4) |
| `GET` | `/ml/batches/registry` | None | Lists all active manufacturing batches |
| `POST` | `/ml/batches/registry` | `{"id": str, "code": str, "warehouse": str, ...}` | Dynamically registers a new production batch |
| `POST` | `/ml/serious` | `{"text": str, "trust_verdict": str}` | Scans for fire, shock, burn, explosion hazards |
| `POST` | `/ml/embed` | `{"texts": List[str], "kind": "query" \| "passage"}` | Generates 384-d normalized embeddings |
| `POST` | `/ml/graph-rebuild` | `{"mentions": List[dict], "product_baseline_neg_rate": float}` | Feature-level issue graph and cluster classifier |
| `POST` | `/ml/confidence` | `{"cluster": dict, "total_product_reviews": int, ...}` | 5-term confidence formula with waterfall breakdown |
| `POST` | `/ml/compare` | `{"lens": str, "group_a": dict, "group_b": dict}` | Statistical comparison across 5 lenses |
| `POST` | `/ml/survey/draft` | `{"product_name": str, "feature": str, ...}` | Drafts targeted follow-up survey questions |
| `POST` | `/ml/survey/ingest` | `{"questions": list, "answers": dict, "current_confidence": float}` | Ingests responses and recalibrates cluster confidence |

---

## 5. Configuration & Calibrated Thresholds (`config/thresholds.yaml`)

```yaml
trust:
  min_char_length: 15
  min_word_count: 3
  g4_cosine_threshold: 0.92
  g5_burst_zscore: 3.0
  verified_purchase_bonus: 0.15

features:
  min_anchor_similarity: 0.72
  margin_over_secondary: 0.04
  neutral_band: 0.15

ambiguity:
  sarcasm_confidence_multiplier: 0.75
  vague_confidence_multiplier: 0.85

batch:
  b0_conf: 1.00
  b1_conf: 0.85
  b2_conf: 0.70
  b3_conf: 0.50
  b4_conf: 0.30

graph:
  graph_sim_threshold: 0.82
  min_cluster_size: 4
  batch_defect_p_value_threshold: 0.01
  max_batch_span_days: 21
  min_batch_dominance: 0.70

confidence:
  w_frequency: 0.25
  w_duration: 0.20
  w_cohort: 0.20
  w_trust: 0.15
  w_evidence: 0.20
  baseline_coherence_bonus: 0.05
```

---

## 6. Development, Operating & Testing Instructions

### 6.1 Environment & Cache Isolation (D: Drive Rules)
All dependencies, virtual environments, and Hugging Face weights must reside on the **D: drive**:
- Virtual Environment: `d:\neo\hachathon\hack malenadu\prism\PRISM\.venv`
- Hugging Face Cache: `d:\neo\hachathon\hack malenadu\prism\PRISM\.hf_cache`
- Pip Cache: `d:\neo\hachathon\hack malenadu\prism\PRISM\.pip_cache`

### 6.2 Starting the Service
Run the automated launcher from workspace root:
```powershell
.\start_ml.ps1
```
Or directly via Python:
```powershell
$env:HF_HOME = "$PSScriptRoot\.hf_cache"
$env:PYTHONPATH = "$PSScriptRoot\ml_service;$PSScriptRoot"
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\uvicorn.exe ml_service.main:app --host 127.0.0.1 --port 8001 --reload
```

### 6.3 Executing the Test Suites
All tests reside in `ml_tests/` and are executed via:
```powershell
.\run_tests.ps1
```
This triggers:
1. `ml_tests/run_test1.py`: 25 adversarial tests across all 10 invariants.
2. `ml_tests/run_test2.py`: 100k hard adversarial stress test suite (`PRISM_100k_hard_cases.jsonl`) sampling across all 9 stages.
3. `ml_tests/run_test3.py`: Real-World Amazon Reviews Benchmark (`test_data/amazon_appliances_20k.jsonl`, 20,000 reviews balanced across ratings 1.0–5.0 with seed 20261026). Ingests real e-commerce data to audit schema conformance, high-throughput pipeline execution, decoupled rating preservation on short reviews, and serious safety hazard detection.
4. `ml_tests/run_all.py`: Unit and integration suite across all 10 ML subsystems.
5. `ml_tests/test_api_endpoints.py`: End-to-end FastAPI endpoint integration suite (16 tests).

---

## 7. Change Log & Maintenance Protocol
Whenever changes are made to any model under `ml_service/models/`:
1. **Never edit `existing_prism`**: Keep the legacy repository untouched as an archival reference.
2. **Verify Invariants**: Run `.\run_tests.ps1` and verify all 23 adversarial cases and 14 API tests pass.
3. **Update This Specification**: Document new parameters in Section 5 and new endpoints in Section 4.
