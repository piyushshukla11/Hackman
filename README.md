# PRISM FRONTEND (Remodeled)

> **Cross-channel, multilingual customer review intelligence. Diagnosis, not summaries.**  
> *Frontend Engineering Specification & Modernized UI Suite.*

This repository contains the completely remodeled, state-of-the-art frontend application for **PRISM**. It is built from the ground up to realize the architecture and visual requirements outlined in `docs2`, while preserving the signature **Landing Page** and the interactive **Simulation Pages**.

---

## 1. Role of the Frontend Engineer

As the frontend engineer on the PRISM team, our mandate is:
1. **Show the reasoning, not just the result.** Every signature visual must bring to light something *only PRISM can do* (batch issue attribution, trust gate cascades, translation diffs, confidence waterfalls, and closed-loop survey validation).
2. **Every animation is backed by real backend events.** There are no artificial or looping animations without an underlying state change. The UI connects directly to a live Server-Sent Events (SSE) stream (`/stream`), visually animating stage transitions, quarantine ejections, and confidence updates only when the backend emits them.
3. **Strictly honest data — zero mock fallbacks.** Empty, loading, and error states are honest and informative. Every aggregate metric explicitly shows its support sample count $n$, quarantined review count, and a direct link to the underlying evidence.
4. **The Signature Forensic Aesthetic.** White light entering a prism and splitting into distinct spectral feature beams. Deep chromatic surfaces (`#06080e`), crisp glassmorphic panels, and high-contrast, accessible typography.
5. **Preserve proven assets.** The original **Landing Page** (with WebGL 3D Prism, About modal, and Tutorial carousel) and the **Simulation Pages** (`amazon.html`, `flipkart.html`, `jiomart.html`, `brand.html`) are preserved and seamlessly wired into the ecosystem.

---

## 2. Directory Structure

```
PRISM FRONTEND/
├── README.md                          # This file — overview & developer guide
├── docs/                              # Detailed engineering specifications
│   ├── ARCHITECTURE.md                # Presentation-first architecture & SSE pipeline
│   ├── DESIGN_SYSTEM.md               # Forensic Prism design tokens, colors & motion
│   ├── ROUTES_AND_SPECS.md            # Detailed routes, component tree & schemas
│   ├── SIGNATURE_VISUALS.md           # The 8 Signature Visuals engineering spec
│   ├── STATE_AND_API.md               # TanStack Query, Zustand SSE store & API contracts
│   ├── ROLE_LENSES.md                 # QA, Ops, Support, Marketing & Leadership lenses
│   └── SIMULATION_INTEGRATION.md      # Preserved simulation pages & multi-store ingestion
├── landing/                           # PRESERVED: Original landing page & WebGL canvas
│   ├── LandingPage.jsx                # Landing page hero with 3D prism & navigation
│   ├── AboutPage.jsx                  # About PRISM modal & feature showcase
│   ├── TutorialPage.jsx               # Guided tutorial slide deck
│   └── components/                    # WebGL shaders & canvas effects
│       ├── Prism.jsx / Prism.css
│       ├── PrismaticBurst.jsx / .css
│       ├── Dither.jsx / .css
│       └── Waves.jsx / .css
├── simulation/                        # PRESERVED: Platform storefront simulations
│   ├── amazon.html                    # Amazon storefront mock with review submit
│   ├── flipkart.html                  # Flipkart storefront mock
│   ├── jiomart.html                   # JioMart storefront mock
│   ├── brand.html                     # Direct-to-Consumer brand store mock
│   ├── simulation.js                  # Shared simulation engine & API dispatcher
│   ├── simulation.css                 # Storefront styles & review modal
│   ├── reviews-data.js                # Multi-platform seed dataset (~400 reviews)
│   └── seed-data.js                   # Product catalog & pricing data
└── src/                               # New Remodeled React App (to be built)
    ├── api/                           # Typed API clients (FastAPI / Render backend)
    ├── components/                    # Atomic, reusable UI components
    │   ├── common/                    # Buttons, modals, tooltips, trust badges
    │   ├── visual/                    # 8 Signature Visuals
    │   └── layout/                    # Left navigation rail, role lens bar, trust header
    ├── pages/                         # Route views (/overview, /stream, /issues, etc.)
    ├── store/                         # Zustand stores (SSE listener, auth, role lens)
    └── types/                         # TypeScript interfaces for classified outputs
```

---

## 3. Technology Stack

| Layer | Choice | Rationale |
| :-- | :-- | :-- |
| **Framework** | **React 18 + Vite + TypeScript** | Type-safe classified backend schemas, instant HMR, fast builds |
| **Styling** | **Tailwind CSS + CSS Variables** | Custom token system, dark-mode native, forensic color spectrum |
| **Component Primitives** | **shadcn/ui + Radix UI** | Unstyled, accessible primitives with total styling control |
| **Data Fetching** | **TanStack Query (React Query v5)** | Cache management, optimistic mutations, window focus refetching |
| **Realtime Stream** | **Zustand + Native EventSource (SSE)** | Listens to Postgres `LISTEN/NOTIFY` via FastAPI `/stream` |
| **Complex Visualizations**| **D3.js + Visx + SVG** | Force-directed graphs, timelines, waterfalls, lead-time scrubber |
| **Micro-Animations** | **Framer Motion** | Physics-based spring animations triggered by SSE events |
| **Icons** | **Lucide React** | Clean, minimalist, consistent icon set |

---

## 4. The 8 Signature Visuals

1. **Prism Stream (`/stream`)**: Raw incoming reviews represented as white light particles. Spam/bot reviews are ejected sideways with reason tags; Hinglish sentences visibly morph into translated English; feature tags attach dynamically before splitting into coloured spectral beams.
2. **Review X-Ray (`/reviews/:id`)**: Forensic breakdown of a single review. Displays word-level feature highlight spans, sarcasm/mixed polarity triggers, original vs. Sarvam translation diff, and the 6-gate trust cascade audit trail.
3. **Forensic Lead-Time Timeline (`/timeline`)**: Multi-channel horizontal swimlanes showing complaint arrivals, automatic batch capsule clustering around anomalies, and the flat 4.4 average rating line contrasted against the simulated returns surge.
4. **Confidence Waterfall (`/issues/:id`)**: Deconstructive bar chart stacking Frequency, Density, Consistency, Temporal proximity, and Evidence strength, adjusted by the Ambiguity Penalty and Coherence Bonus, showing exact review backing on hover.
5. **Batch Flow Map & Language Heatmap**: Geospatial flow from warehouse $W_2$ through distribution channels to regional clusters across India, paired with an Indic language density map.
6. **Closed-Loop Survey Thread (`/investigations`)**: Interactive customer clarification conversation. When an automated verification survey is answered, the issue confidence score visibly moves (e.g., $0.68 \rightarrow 0.84$).
7. **Comparison Engine (`/compare`)**: Statistical multi-lens comparison across 5 dimensions: Product, Time, Batch, Channel, and Version with Wilson score confidence intervals and plain-language verdicts.
8. **Trust & Quarantine Header Bar**: Persistent top-bar metric displaying total reviews versus quarantined reviews, complete with a global toggle to audit metrics with or without filtered reviews.

---

## 5. Documentation Map

Refer to the documents in `docs/` for complete implementation details:

* **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**: Architectural boundaries, data flow, and SSE event streaming.
* **[docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md)**: Color tokens, spectral palette, typography, glassmorphism, and animation rules.
* **[docs/ROUTES_AND_SPECS.md](docs/ROUTES_AND_SPECS.md)**: Complete route catalog, page layouts, component trees, and data requirements.
* **[docs/SIGNATURE_VISUALS.md](docs/SIGNATURE_VISUALS.md)**: Engineering guide for building the 8 signature visuals.
* **[docs/STATE_AND_API.md](docs/STATE_AND_API.md)**: API endpoints, TypeScript models, TanStack Query hooks, and Zustand store design.
* **[docs/ROLE_LENSES.md](docs/ROLE_LENSES.md)**: Role-specific view configurations (QA, Ops, Support, Marketing, Leadership).
* **[docs/SIMULATION_INTEGRATION.md](docs/SIMULATION_INTEGRATION.md)**: Storefront simulation architecture, review generation, and multi-channel ingestion.

---

## 6. How the Preserved Assets Work

### Landing Page (`landing/`)
The landing page features a GPU-accelerated WebGL 3D Prism that rotates interactively in response to user motion. It exposes:
- **Hero Display**: Sleek typography with PRISM branding and tagline.
- **About Modal**: In-depth explanations of the 5-layer intelligence pipeline.
- **Tutorial Modal**: 10-slide interactive walkthrough explaining the health score, feature extraction, graph clustering, and lead-time advantage.
- **Sign In Action**: Invokes the application navigation trigger to transition seamlessly into the authenticated dashboard.

### Simulation Pages (`simulation/`)
Each simulation page is an autonomous storefront with its own DOM structure and theme:
- `amazon.html`: Amazon India dark-nav interface with product picker, buy box, and review submission.
- `flipkart.html`: Flipkart blue/yellow interface with verified buyer badging.
- `jiomart.html`: JioMart grocery & electronics layout.
- `brand.html`: Minimalist direct-to-consumer store.

All four storefronts share `simulation.js`, which manages local reviews display and dispatches user-submitted reviews to `POST http://localhost:5000/api/reviews/ingest` (or the `/v1/ingest/` gateway), instantly incrementing the real-time live review counter across all open windows.
