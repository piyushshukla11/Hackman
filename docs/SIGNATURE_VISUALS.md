# PRISM Signature Visuals Specification

This document provides complete engineering specifications for the **8 Signature Visuals** that define PRISM's user experience. Each visual makes tangible something *only PRISM can do*, moving beyond generic dashboards into deep forensic intelligence.

---

## 1. Prism Stream (`/stream`)

### Purpose
Visualizes the real-time processing of reviews through the 5-layer pipeline. It embodies the optical prism metaphor: incoming messy multi-channel feedback arrives as raw white light, undergoes automated cleansing and translation, and refracts into distinct spectral feature beams.

### Visual Elements & Architecture
- **Inbound Chamber (L1 Ingest)**: Raw review packets emerge as glowing white particles entering from the left. Each particle carries metadata tooltips (source platform, timestamp, author hash).
- **Trust Gate Prism (L2 Clean)**: Particles strike the central prism:
  - **Spam & Bot Ejection**: Particles flagged by gates G1-G6 (duplicates, bursts, promotion templates) are deflected down into a "Quarantine Chamber" with visible reason tags (`SHORT_TEXT`, `EXACT_DUP`, `BURST`).
  - **Language Normalization & Translation**: Hinglish or Indic-script particles briefly glow and display their clean English translation above the particle (`"Sound mast hai but box pichka"` $\rightarrow$ `"Sound is great but box was crushed"`).
- **Refraction & Spectral Separation (L3 & L4)**:
  - Feature tags attach dynamically to the particles.
  - The single white stream splits into 5–7 colored spectral beams (Cyan for Battery, Amber for Packaging, Blue for Build Quality, etc.).
  - Particles accelerate along their corresponding feature beam into the active issue buckets.
- **Backend Retries**: If a Render Workflow task retries, the particle stutters and displays an attempt indicator badge (`Attempt 2/3`) linking directly to the Render task log.

### Data Contracts
- Subscribed to SSE events: `review.stage` (stage, status, attempt, duration_ms) and `trust.verdict` (reason_code, score_delta).
- On particle click: opens side-drawer with `GET /v1/reviews/{id}` payload.

---

## 2. Review X-Ray (`/reviews/:id`)

### Purpose
Forensic transparency for an individual review, showing the exact NLP reasoning, trust audit trail, translation diffs, and feature-anchor similarities.

### Visual Components
1. **Interactive Highlight View**: Review text broken down into tokens and clauses. Hovering highlights the exact sentence and shows:
   - Extracted feature tag and sentiment polarity (+ / -).
   - Word-level anchor similarity score (e.g., `similarity: 0.74` to `"box, packaging, unboxing"`).
2. **Ambiguity & Sarcasm Bar**:
   - Contradiction flag: Displays rating vs. text tension (e.g., 4.5 stars + severe packaging complaint = classified as `mixed`, not `sarcasm`).
   - Sarcasm signals triggered (e.g. `irony_markers`, `contrast_clause`, `lang_tier`).
   - Multiplier pill: `1.00` (None), `0.85` (Vague), `0.70` (Mixed), `0.55` (Sarcasm).
3. **Language & Translation Diff**: Split-screen view comparing original text (`text_original`) with normalized English (`text_en`), highlighting translated tokens and masked PII entities.
4. **Trust Gate Audit Cascade**: Chronological vertical stepper for Gates G1 to G6:
   - G1 Length ($\ge 2$ words) — Pass/Fail.
   - G2 Exact Duplication — Hash match check.
   - G3 Near-Duplicate Embedding — Cosine similarity vs. catalog ($< 0.95$).
   - G4 Content Heuristics — Promo, links, shill patterns.
   - G5 Burst & Coordination — Z-score velocity check.
   - G6 Provenance & Verified Purchase — Bonus calculation.
   - Final Trust Score with resulting rating status (`counted`, `downweighted`, `excluded`).

---

## 3. Forensic Lead-Time Timeline (`/timeline`)

### Purpose
Proves PRISM's primary value proposition: **early defect diagnosis before viral escalation or return spikes**. Answers: *"PRISM detected this on Day 4; traditional return signals didn't spike until Day 19."*

### Visual Components
1. **Multi-Channel Swimlanes**: Horizontal parallel lanes for Amazon, Flipkart, JioMart, Brand Site, and Widget/Extension.
2. **Complaint Nodes**: Coloured dots plotted at exact review arrival times.
3. **Batch Capsule Snapping**: When 4+ complaints match a specific batch (e.g., Batch `B-0716`), an animated SVG bounding capsule snaps around the nodes, displaying:
   - `Batch Defect Identified (Confidence 0.84)`
   - Affected window: 9 days.
   - Warehouse origin: $W_2$.
4. **Dual Indicator Overlay**:
   - **Average Rating Curve**: A flat, seemingly safe 4.4-star line that fails to warn management.
   - **Defect Detection Pin**: Placed at Day 4 ("PRISM Flagged").
   - **Simulated Returns Series**: Placed at Day 19 ("Customer Returns Surged +310%").
5. **Interactive Time Scrubber**: A playback slider that replays the timeline day-by-day, showing how confidence accumulated and why traditional metrics lagged.

---

## 4. Confidence Waterfall (`/issues/:id`)

### Purpose
Demystifies PRISM's diagnosis confidence score. Shows exactly which mathematical terms contributed to the score, preventing "black-box" skepticism.

### Formula Visualization
$$\text{Base} = 0.25\cdot\text{Freq} + 0.20\cdot\text{Density} + 0.20\cdot\text{Consistency} + 0.15\cdot\text{Temporal} + 0.20\cdot\text{Evidence}$$
$$\text{Confidence} = \text{clamp}\big(\text{Base} \times \text{AmbiguityPenalty} + \text{CoherenceBonus} + \text{SurveyDelta}, 0, 1\big)$$

### Visual Components
- **Stacked Waterfall Bars**:
  1. **Frequency (+)**: Lift over historical baseline.
  2. **Cluster Density (+)**: Total interconnected feature mentions.
  3. **Semantic Consistency (+)**: Average pairwise cosine similarity of review embeddings.
  4. **Temporal Proximity (+)**: Fit to `batch_spike` decay curve.
  5. **Evidence Strength (+)**: Trust-weighting and photo/label OCR verification.
  6. **Ambiguity Penalty (-)**: Discount for vague or sarcastic reviews.
  7. **Coherence Bonus (+)**: Bonus if $>50\%$ of node pairs have strong similarity.
  8. **Survey Delta ($\pm$)**: Direct boost from validated customer replies.
- **Interactive Drill-down**: Hovering any waterfall segment reveals the specific reviews driving that sub-score.

---

## 5. Batch Flow Map & Language Heatmap

### Purpose
Visualizes the physical and linguistic footprint of emerging defects across India's supply chain.

### Visual Components
- **Supply Chain Sankey / Flow Map**:
  - Connects Manufacturing Facility $\rightarrow$ Regional Warehouse ($W_2$) $\rightarrow$ Retail Channels (Amazon, Flipkart, Brand) $\rightarrow$ Destination Zones.
  - Highlights compromised routes in glowing amber/red when a batch defect is isolated.
- **Choropleth Language Density Map**:
  - Map of Indian states colored by review volume and language breakdown (Hindi, Hinglish, Tamil, Kannada, Bengali, etc.).
  - Pinpoints region-specific terminology issues versus universal hardware defects.

---

## 6. Closed-Loop Survey Thread (`/investigations`)

### Purpose
Demonstrates PRISM's active verification loop (L5 Act). Shows how automated follow-up surveys to consented reviewers validate ambiguous findings and update system confidence.

### Visual Components
- **Investigation Conversation View**: Displays the AI-generated diagnostic survey sent to customer emails:
  - Example: *"Did the inner packaging cushion arrive damaged, or was the outer corrugated box torn?"*
- **Response Feed**: Real-time incoming customer responses.
- **Live Confidence Mover**:
  - When a customer submits a survey reply via the mobile web view, an SSE event triggers in the dashboard.
  - The issue's confidence gauge visibly moves with an animated counter (e.g. from $0.62$ `Monitor` to $0.81$ `Act`).
  - An audit badge appears: `Verified by 3 Consented Customers`.

---

## 7. Comparison View & Site Performance Matrix (`/compare`)

### Purpose
Eliminates five custom reporting dashboards with a single, multi-lens comparison engine.

### Supported Lenses
1. **Product Lens**: Product A vs. Product B in same category.
2. **Time Lens**: Current month vs. previous month.
3. **Batch Lens**: Batch `B-0716` vs. historical batch baseline.
4. **Channel Lens**: Amazon vs. Flipkart vs. Brand Store for identical SKU.
5. **Version Lens**: Version 1.0 vs. Version 2.0 (after product modification).

### Visual Components
- **Performance Matrix Table**: Channels/Products as rows, features as columns. Cells display trust-weighted sentiment and sample counts.
- **Statistical Delta Card**:
  - Displays difference $\Delta$ with Wilson Score confidence intervals.
  - Plain-language verdict: `Statistically Significant Improvement (p = 0.004)`.
  - Top contributing factors breakdown.

---

## 8. Trust & Quarantine Header Bar

### Purpose
Establishes data integrity and auditability at the top of every dashboard view.

### Visual Components
- **Global Metric Pill**: Persistent in the main top navigation:
  `Total Reviews: 1,482 | Trusted: 1,344 | Quarantined: 138 (9.3%)`
- **Quarantine Mode Switch**: A quick toggle:
  - `[x] Filtered (Headline)`: Only counts reviews passing trust gates (weight $\ge 0.40$).
  - `[ ] Raw (All Reviews)`: Includes suspicious and bot reviews to audit the delta.
- **Quarantine Drawer Trigger**: Clicking the count opens a drawer listing all quarantined items, their assigned reason codes (`SHORT_TEXT`, `BOT_BURST`, `EXACT_DUP`), and reviewer trust scores.
