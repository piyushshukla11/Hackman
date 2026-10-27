# PRISM Routes and Page Specifications

This document defines the complete routing architecture, page layouts, components, and data dependencies for the remodeled PRISM Frontend.

---

## 1. Route Table Overview

| Route | Page Name | Primary Objective | Signature Elements |
| :-- | :-- | :-- | :-- |
| `/` | **Landing Page** | First impression, product overview & auth gate | WebGL 3D Prism, About modal, Tutorial carousel |
| `/overview` | **Portfolio Overview** | Executive summary, portfolio health, active alerts | Health Score Card, Issue Feed, Source Strip |
| `/stream` | **Prism Stream** | Live pipeline visualization & event stream | Particle Canvas, Feature Refractor, Quarantine Bin |
| `/issues` | **Issue Directory** | Prioritized list of systemic & batch defects | Filterable Cards, Severity Badges, Confidence Bars |
| `/issues/:id` | **Issue Deep Dive** | Root-cause diagnosis & evidence audit | **Confidence Waterfall**, Member Reviews, Action Card |
| `/reviews/:id`| **Review X-Ray** | Single-review forensic inspection | Word highlights, Sarcasm analysis, Trust Gates |
| `/timeline` | **Forensic Timeline** | Early defect detection vs. return lag proof | Multi-channel swimlanes, Batch Capsule, Scrubber |
| `/compare` | **Comparison Engine** | Statistical multi-lens comparison | 5 Lenses, Wilson CIs, Significance Verdict |
| `/products/:id`| **Product Catalog**| Versioning, modifications, channel performance | Version timeline, Modification impact card |
| `/serious` | **Safety Triage Queue**| Real-time serious hazard & safety alerts | Urgency badges, Incident details, Slack link |
| `/investigations`| **Survey Loop** | Closed-loop customer clarification | Survey thread, **Live Confidence Mover** |
| `/sources` | **Source Health** | Monitor 6 simulated sites & API ingest status | Drift monitor, Volume EWMA sparklines, Freshness |
| `/reports` | **Executive Reports** | PDF report generation & export history | PDF visualizer, One-click WeasyPrint generator |
| `/settings` | **System Settings** | Catalog management, API keys, Widget generator | Taxonomies, Batch registry, Snippet embed |
| `/judge` | **Judge Mode (90s)** | Guided rapid evaluation walkthrough | Auto-play stepper, Render task correlation |

---

## 2. Detailed Page Specifications

### 2.1 Landing Page (`/`) — Preserved Asset
- **Status**: Preserved from the original frontend codebase (`landing/LandingPage.jsx`).
- **Features**:
  - Fullscreen WebGL rotating 3D prism with reactive refraction shaders.
  - Minimalist navigation header with "About", "Tutorial", and "Login".
  - About modal highlighting PRISM's 5 layers (Ingest, Clean, Understand, Diagnose, Act).
  - 10-slide interactive tutorial modal explaining health scoring and lead-time advantage.
  - "Enter Dashboard" button which triggers the route guard to transition into the main application.

---

### 2.2 Portfolio Overview (`/overview`)
- **Components**:
  - `HealthScoreCard`: Large composite health score (0–100) with trust-weighted baseline.
  - `ProductSummaryBanner`: Steam-style dynamic summary string (e.g. *"Moderately Positive (64%), driven by Packaging issues in Batch B-0716"*).
  - `TopIssuesList`: Top 5 urgent issues ranked by $\text{Confidence} \times \text{Severity}$.
  - `SourceHealthStrip`: Compact status row showing latency and status of all 6 data ingestion sources.
  - `WhatChangedThisWeek`: Micro-trend indicators showing positive or negative momentum per feature.

---

### 2.3 Prism Stream (`/stream`)
- **Components**:
  - `PrismStreamCanvas`: High-performance canvas/SVG rendering live review particles.
  - `StageLaneBar`: Progress indicators showing active tasks across L1 to L5.
  - `QuarantineTray`: Bottom container collecting discarded reviews with clickable reason chips.
  - `LiveEventFeed`: Monospaced real-time log of `pipeline_events` from the SSE socket.

---

### 2.4 Issue Detail & Confidence Waterfall (`/issues/:id`)
- **Components**:
  - `IssueHeader`: Feature badge, classification chip (`batch | systemic | isolated`), severity, and affected units.
  - `ConfidenceWaterfall`: SVG bar chart displaying all 8 mathematical terms contributing to the confidence score.
  - `RecommendedActionBox`: Grounded, actionable prescription from the feature $\times$ issue type matrix.
  - `MemberEvidenceList`: Filterable, paginated review snippets with direct links to `/reviews/:id` (X-Ray).

---

### 2.5 Review X-Ray (`/reviews/:id`)
- **Components**:
  - `HighlightedReviewBody`: Interactive text component with token-level feature matches and anchor cosine similarity tooltips.
  - `TranslationDiffPanel`: Side-by-side comparison of original Indic/Hinglish text vs. normalized English.
  - `TrustGateLog`: Step-by-step breakdown of gates G1 through G6 with pass/warn/fail badges and score deltas.
  - `RatingTextConflictMeter`: Visual gauge indicating divergence between numeric star rating and text sentiment.

---

### 2.6 Forensic Timeline (`/timeline`)
- **Components**:
  - `SwimlaneCanvas`: Interactive D3 timeline with 4+ parallel channel lanes.
  - `BatchCapsuleLayer`: Dynamic SVG capsules grouping reviews sharing batch attributes.
  - `LagComparisonChart`: Overlay line chart showing average rating line vs. returns spike curve.
  - `ScrubberControl`: Play/pause, step forward/back, and speed multiplier controls for presentation replay.

---

### 2.7 Comparison Engine (`/compare`)
- **Components**:
  - `LensSelector`: 5-button tab selector (`Product`, `Time`, `Batch`, `Channel`, `Version`).
  - `GroupConfigurator`: Select Group A and Group B targets.
  - `StatisticalSummaryCard`: Visual display of difference $\Delta$, Wilson confidence intervals, and Mann-Whitney U test p-values.
  - `FeatureDeltaBars`: Horizontal divergence bars showing which features drove the shift.

---

### 2.8 Closed-Loop Investigations (`/investigations`)
- **Components**:
  - `ActiveInvestigationsList`: Ongoing customer clarification surveys with countdown timers.
  - `SurveyThreadView`: Mobile-style preview of the 4 diagnostic questions dispatched to the customer.
  - `ResponseStream`: Inbound customer responses with LLM-generated summaries.
  - `ConfidenceMoverWidget`: Live dial showing the confidence delta applied upon response ingestion.

---

### 2.9 Judge Mode (`/judge`)
- **Components**:
  - `JudgeStepperBar`: Progress tracker across the 7 evaluation stops (Stream $\rightarrow$ X-Ray $\rightarrow$ Timeline $\rightarrow$ Waterfall $\rightarrow$ Survey $\rightarrow$ Version Compare $\rightarrow$ Render Architecture).
  - `ReplaySpeedSelector`: 1x, 2x, or Instant replay options.
  - `EvaluationCard`: Bullet points summarizing the technical merit and novel contribution of the current step.
