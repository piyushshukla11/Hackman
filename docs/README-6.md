# PRISM (remake)

**Cross-channel, multilingual customer review intelligence. Diagnosis, not summaries.**

PRISM takes scattered reviews and ratings from many channels and languages and answers:
**which feature, which batch or version, which channel, since when, how sure are we, and what should we do.**

> Example: 6 packaging complaints in 3 languages across 3 channels; the average rating is still 4.4.
> PRISM flags a probable batch issue within days, with evidence, confidence and a recommended action.

---

## What PRISM actually does (5 layers)

```
 L1 INGEST    get reviews + ratings in, with provenance (APIs, widget, extension, files)
    |
 L2 CLEAN     language/script, translation, trust cascade (bots, dupes), rating kept even if text is rejected
    |
 L3 UNDERSTAND  feature-level sentiment, sarcasm/ambiguity, batch inference, serious-complaint scoring
    |
 L4 DIAGNOSE  issue graph, isolated/batch/systemic/channel classification, trends, comparisons, confidence
    |
 L5 ACT       verification surveys, email, alerts, weekly digests, company report PDF
```

Every layer is a Python module with a typed input and output (see `architecture.md`). Every insight links back to the reviews and evidence behind it.

## What is different from a review summariser

- Ties complaints to **batches, versions and channels**, not just topics.
- Rating (0.5-step stars) is a first-class signal, separate from text.
- Trust is a **score with reasons**, shown next to every metric.
- Uncertain findings are **verified with customers** and the confidence moves.
- Product, time, batch, channel and version comparisons come from one comparison engine.

## Documents

| File | Purpose |
| :-- | :-- |
| `README.md` | This overview |
| `architecture.md` | Services, modules, data model, backend outputs, API, Render layout, CI/CD |
| `pipeline.md` | Stage-by-stage logic, formulas, reason codes, Render task mapping |
| `data_source.md` | Ingestion lanes, 6 placeholder simulated sites, widget, extension, source health |
| `ml.md` | Models, language strategy, sarcasm/ambiguity, thresholds, evaluation |
| `basic_frontend.md` | Interfaces, pages, visuals, data each visual needs, Judge mode |
| `features_and_decisions.md` | Feature list per MVP, decision log, cuts, risks |

## Stack at a glance

| Part | Choice |
| :-- | :-- |
| API | Python 3.12, FastAPI, Pydantic v2 |
| Durable pipeline | Render Workflows (Python tasks) |
| DB | Render Postgres + pgvector, SQLAlchemy 2, Alembic |
| ML | `intfloat/multilingual-e5-small` (384-d, ONNX int8), full 7,500-word `vaderSentiment` + Hinglish lexicon, Sarvam translate, RAG-grounded Gemini for diagnostic surveys & ambiguity second-pass, label OCR |
| Dashboard | React + Vite + TypeScript + Tailwind + shadcn/ui |
| Widget | Vanilla TypeScript, one small bundle |
| Extension | Chrome MV3, TypeScript |
| Simulated sites | 6 placeholder sites (small Node or static apps) |
| Email | Provider API (Resend or Postmark style) behind our own email module |
| Reports | HTML to PDF (WeasyPrint) in the backend |
| CI/CD | GitHub Actions + Render Blueprint (`render.yaml`) auto-deploy |

## Suggested repo layout

```
prism/
  README.md  docs/
  apps/
    api/            FastAPI app (read API, ingest gateway, survey pages, SSE)
    workflows/      Render Workflows tasks (thin wrappers over prism_core)
    dashboard/      React app
    widget/         embeddable widget
    extension/      MV3 extension
    sim-sites/      6 placeholder storefronts + their mock review APIs
  prism_core/       Python package: all domain modules (see architecture.md)
  seeds/            seeded demo + eval datasets, generators
  infra/            render.yaml, Dockerfiles
  .github/workflows/
```

## Build order (MVPs)

1. Gateway, adapters, rating normalisation, Postgres
2. Trust cascade and trust score (text and rating)
3. Extraction, sarcasm/ambiguity, LLM second pass
4. Batch inference and issue graph
5. Comparison engine (product, time, batch, channel, version) and confidence
6. Survey loop and email
7. Widget and extension
8. Company report PDF, source health, eval harness, Judge mode

## Ground rules

- No mock data fallbacks anywhere. Empty and error states are honest.
- Every animation in the UI is driven by a real backend event.
- Thresholds live in config and are calibrated by the eval harness, not hardcoded.
- Scope: digital, product-based sources only. No social media or public-service sources.
