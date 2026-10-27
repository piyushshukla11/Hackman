# PRISM Frontend Architecture

## 1. Principles

1. **Presentation-First, Intelligence-Driven Backend**: The frontend does not calculate business metrics, cluster issues, or make heuristic guesses. The Python/FastAPI backend computes and classifies all domain objects (`TrustVerdict`, `ReviewAnalysis`, `IssueCard`, `SeriousComplaint`, `Comparison`, `TrendIndex`, `Investigation`, `Report`, `SourceHealth`). The frontend faithfully and dynamically visualizes them.
2. **Event-Driven Reactive UI**: The interface maintains a single, resilient Server-Sent Events (SSE) connection to `GET /stream` (backed by PostgreSQL `LISTEN / NOTIFY`). Visual events (e.g. stage progress in Prism Stream, quarantine alerts, new serious complaints, survey response deltas) animate strictly in response to real server-emitted events.
3. **Auditability & Honest Representation**: No fabricated or mock metrics. Every card and metric displays support counts $n$ and the number of quarantined reviews. The global trust header allows toggling between "Clean only" and "Including quarantined" views.
4. **Deep Chromatic Aesthetics (Forensic Prism)**: Dark obsidian canvas (`#06080e`), crisp glassmorphic panels (`rgba(255, 255, 255, 0.04)`), and dynamic spectral feature rays representing product features.

---

## 2. System Context & Data Flow

```
   ┌─────────────────────────────────────────────────────────────┐
   │                     BACKEND SERVICES                        │
   │  FastAPI (Read API + Ingestion Gateway)                     │
   │  Render Workflows (Durable Tasks: Ingest, Clean, Understand)│
   │  PostgreSQL + pgvector (Data Store & LISTEN/NOTIFY)         │
   └───────────────▲─────────────────────────────┬───────────────┘
                   │                             │
     HTTP REST     │                             │ Server-Sent Events (SSE)
     (Queries/     │                             │ (/stream)
     Mutations)    │                             │
                   │                             ▼
   ┌───────────────┴─────────────────────────────────────────────┐
   │                 PRISM FRONTEND APPLICATION                  │
   │                                                             │
   │   ┌─────────────────────┐       ┌────────────────────────┐  │
   │   │  TanStack Query v5  │       │     Zustand Store      │  │
   │   │  (REST Data Cache)  │       │ (SSE Stream & Events)  │  │
   │   └──────────┬──────────┘       └───────────┬────────────┘  │
   │              │                              │               │
   │              ▼                              ▼               │
   │   ┌──────────────────────────────────────────────────────┐  │
   │   │             Signature Visuals & Pages                │  │
   │   │  - Prism Stream Canvas (Particles & Beams)           │  │
   │   │  - Review X-Ray (Highlighting & Trust Cascade)       │  │
   │   │  - Forensic Timeline (Channel Lanes & Batch Capsule) │  │
   │   │  - Confidence Waterfall (Breakdown Stacks)           │  │
   │   │  - Comparison Engine (5 Lenses + Wilson CIs)         │  │
   │   │  - Closed-Loop Survey Thread & Confidence Mover      │  │
   │   └──────────────────────────────────────────────────────┘  │
   └─────────────────────────────────────────────────────────────┘
```

---

## 3. Classified Backend Output Consumption

Each backend output class maps directly to a typed frontend data consumer:

| Output Class | Source Endpoint | Primary Frontend Consumer |
| :-- | :-- | :-- |
| `TrustVerdict` | `/v1/reviews/{id}/xray`, `/v1/trust/*` | **Review X-Ray**, Trust Gate Breakdown, Header Trust Panel |
| `ReviewAnalysis` | `/v1/reviews/*`, `/v1/reviews/{id}` | Word-level feature highlights, Sarcasm/Mixed tags, Translation diff |
| `IssueCard` | `/v1/issues`, `/v1/issues/{id}` | Issue cards, **Confidence Waterfall**, Batch/Channel badges |
| `SeriousComplaint`| `/v1/serious` | Serious Safety Queue, Alert badges, Priority toast notifications |
| `Comparison` | `/v1/compare?lens=...` | **Comparison Engine** (Product, Time, Batch, Channel, Version) |
| `TrendIndex` | `/v1/trends`, `/v1/overview` | Forensic Timeline, Weekly sentiment trajectory, Spike alerts |
| `Investigation` | `/v1/investigations/{id}` | **Closed-Loop Survey Thread** & Realtime Confidence Mover |
| `SourceHealth` | `/v1/sources/health` | Source Health Monitor Strip, Ingestion Health Table |
| `Report` | `/v1/reports`, `/v1/reports/{id}` | Executive PDF Report viewer and download actions |

---

## 4. State Management Architecture

### A. Server Cache Layer (`TanStack Query v5`)
- Manages all asynchronous REST requests.
- Caches query data with stale-time heuristics (e.g., 30 seconds for overview, 5 minutes for static catalogs).
- Key query hooks:
  - `useOverview(productId, role)`
  - `useIssues(productId, filter)`
  - `useIssueDetail(issueId)`
  - `useReviewXRay(reviewId)`
  - `useComparison(lens, a, b, metric)`
  - `useSourceHealth()`
  - `useInvestigations()`

### B. Realtime Stream Store (`Zustand`)
- Handles the persistent EventSource connection to `/api/stream`.
- Receives typed SSE events:
  - `review.stage`: Updates live pipeline position in Prism Stream.
  - `trust.verdict`: Ejects spam particles or triggers clean pass animation.
  - `issue.updated`: Refetches or patch-updates issue cards and confidence meters.
  - `serious.new`: Triggers urgent notifications and increments queue counters.
  - `survey.reply`: Triggers the live confidence score mover animation ($0.68 \rightarrow 0.84$).
  - `source.health`: Updates source status indicators without page reload.
- Automatically invalidates corresponding TanStack Query cache keys on relevant events.

### C. UI & Lens Store (`Zustand`)
- `roleLens`: Current active role perspective (`qa | operations | support | marketing | leadership`).
- `includeQuarantined`: Boolean toggle for headline metrics auditing.
- `selectedProduct`: Active product ID across portfolio.
- `activeFeatureFilter`: Global feature tag selection for cross-panel filtering.

---

## 5. Navigation & Layout Hierarchy

```
┌────────────────────────────────────────────────────────────────────────┐
│ TOP BAR: Logo | Product Selector | Trust Meter (Quarantine Toggle)     │
│          Role Lens Switcher (QA/Ops/Support/Mktg/Lead) | User Avatar   │
├─────────┬──────────────────────────────────────────────────────────────┤
│ LEFT    │ MAIN VIEWPORT (Routed Views)                                 │
│ RAIL    │                                                              │
│         │  /overview       -> Portfolio health, top issues, alerts     │
│ [Ingest]│  /stream         -> Signature Prism Stream visual            │
│ Sources │  /issues/:id     -> Issue details & Confidence Waterfall     │
│ [Clean] │  /reviews/:id    -> Review X-Ray with Trust Gates            │
│ Stream  │  /timeline       -> Forensic Lead-Time Timeline              │
│ [Under] │  /compare        -> Multi-Lens Statistical Comparison        │
│ Serious │  /products/:id   -> Product versions & modifications         │
│ [Diag]  │  /investigations -> Closed-loop survey thread                │
│ Issues  │  /sources        -> Source health & upload mappings          │
│ Compare │  /reports        -> Executive PDF downloads                  │
│ Timeline│  /settings       -> Batch registries & API keys              │
│ [Act]   │  /judge          -> 90-second guided judge replay path       │
│ Surveys │                                                              │
│ Reports │                                                              │
└─────────┴──────────────────────────────────────────────────────────────┘
```

The left navigation rail is explicitly organized using PRISM's 5-layer mental model (**Ingest, Clean, Understand, Diagnose, Act**), allowing new users and evaluators to intuitively comprehend how raw feedback becomes targeted action.
