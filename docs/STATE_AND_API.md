# PRISM State Management and API Integration

This document specifies the data layer of the remodeled PRISM Frontend: typed schemas, REST API client, TanStack Query hooks, and Zustand real-time SSE stream listeners.

---

## 1. Classified Backend Models (TypeScript Schemas)

```typescript
// --- Trust & Clean ---
export interface TrustGateLogEntry {
  gate: 'G1_LENGTH' | 'G2_EXACT_DUP' | 'G3_NEAR_DUP' | 'G4_CONTENT' | 'G5_BURST' | 'G6_PROVENANCE';
  verdict: 'pass' | 'warn' | 'fail';
  reason_code: string;
  detail: Record<string, any>;
  score_delta: number;
}

export interface TrustVerdict {
  review_id: string;
  trust_score: number; // 0.0 to 1.0
  verdict: 'clean' | 'suspicious' | 'rejected';
  text_status: 'accepted' | 'rejected_short' | 'rejected_spam' | 'rejected_dup' | 'none';
  rating_status: 'counted' | 'downweighted' | 'excluded';
  gates: TrustGateLogEntry[];
}

// --- Understanding & Features ---
export interface FeatureMention {
  feature: string;
  polarity: 'positive' | 'negative' | 'neutral';
  score: number; // Anchor similarity
  ambiguity: 'none' | 'vague' | 'mixed' | 'sarcasm';
  ambiguity_multiplier: number; // 1.0, 0.85, 0.70, 0.55
  matched_sentence: string;
}

export interface ReviewXRay {
  id: string;
  product_id: string;
  channel: string;
  rating_raw: number;
  rating_normalized: number;
  text_original: string;
  text_en: string;
  language: string;
  script: string;
  reviewed_at: string;
  batch_code?: string;
  batch_method: 'B0' | 'B1' | 'B2' | 'B3' | 'B4';
  batch_confidence: number;
  features: FeatureMention[];
  trust: TrustVerdict;
  rating_conflict: boolean;
}

// --- Diagnosis & Issues ---
export interface ConfidenceBreakdown {
  frequency: number; // Lift over baseline
  density: number; // Cluster size
  consistency: number; // Semantic cohesion
  temporal: number; // Spike/creep shape fit
  evidence: number; // Trust * Batch Conf * Media
  ambiguity_penalty: number;
  coherence_bonus: number;
  survey_delta: number;
  final_confidence: number;
}

export interface IssueCard {
  id: string;
  product_id: string;
  feature: string;
  issue_type: 'isolated' | 'batch' | 'systemic' | 'channel_specific' | 'praise';
  severity: 'high' | 'medium' | 'low';
  confidence: number; // 0.0 to 1.0
  confidence_level: 'green' | 'yellow' | 'red';
  confidence_parts: ConfidenceBreakdown;
  affected_batches: string[];
  affected_channels: string[];
  first_seen: string;
  last_seen: string;
  size: number;
  recommendation: string;
}

// --- Comparison Engine ---
export interface ComparisonResult {
  lens: 'product' | 'time' | 'batch' | 'channel' | 'version';
  group_a: { label: string; n: number; metric_value: number };
  group_b: { label: string; n: number; metric_value: number };
  delta: number;
  confidence_interval: [number, number]; // 95% Wilson / Wald CI
  p_value: number;
  verdict: 'better' | 'worse' | 'no_change' | 'insufficient_data';
  top_contributing_features: { feature: string; delta: number }[];
}
```

---

## 2. API Endpoints Map

Base URL: `http://localhost:5000/api` (or Render deployment URL)

| Method | Endpoint | Description |
| :-- | :-- | :-- |
| `GET` | `/v1/overview?product_id={id}&role={role}` | Composite health score, top issues, alerts |
| `GET` | `/v1/reviews/{id}/xray` | Full forensic X-Ray for review |
| `GET` | `/v1/issues` | Filterable list of issue clusters |
| `GET` | `/v1/issues/{id}` | Deep dive and confidence breakdown |
| `GET` | `/v1/compare` | Multi-lens statistical comparison engine |
| `GET` | `/v1/trends` | Time-series rollups, lead-time data |
| `GET` | `/v1/investigations` | Active customer surveys & status |
| `POST`| `/v1/investigations/{issue_id}/survey` | Manually dispatch diagnostic survey |
| `GET` | `/v1/sources/health` | Source health, latency, error rates, drift |
| `POST`| `/v1/reports` | Trigger backend PDF generation |
| `POST`| `/v1/demo/replay` | Replay seed dataset for Judge Mode |
| `GET` | `/v1/stream` | Server-Sent Events (SSE) connection |

---

## 3. Realtime Stream Store (`Zustand`)

The `sseStore` handles the SSE lifecycle and state distribution:

```typescript
// store/useSSEStore.ts
import { create } from 'zustand';

interface PipelineEvent {
  id: string;
  stage: string;
  status: 'running' | 'success' | 'failed' | 'retry';
  review_id?: string;
  attempt: number;
  duration_ms: number;
  detail: any;
  timestamp: string;
}

interface SSEStoreState {
  connected: boolean;
  events: PipelineEvent[];
  recentReviews: any[];
  quarantinedCount: number;
  activeSurveysCount: number;
  connect: () => void;
  disconnect: () => void;
}

export const useSSEStore = create<SSEStoreState>((set, get) => {
  let eventSource: EventSource | null = null;

  return {
    connected: false,
    events: [],
    recentReviews: [],
    quarantinedCount: 0,
    activeSurveysCount: 0,

    connect: () => {
      if (eventSource) return;
      eventSource = new EventSource('/api/v1/stream');

      eventSource.onopen = () => set({ connected: true });
      eventSource.onerror = () => set({ connected: false });

      eventSource.addEventListener('review.stage', (e) => {
        const payload = JSON.parse(e.data);
        set((state) => ({
          events: [payload, ...state.events.slice(0, 99)]
        }));
      });

      eventSource.addEventListener('trust.verdict', (e) => {
        const verdict = JSON.parse(e.data);
        if (verdict.verdict === 'rejected') {
          set((state) => ({ quarantinedCount: state.quarantinedCount + 1 }));
        }
      });

      eventSource.addEventListener('survey.reply', (e) => {
        // Triggers query invalidation in React Query for investigations
      });
    },

    disconnect: () => {
      eventSource?.close();
      eventSource = null;
      set({ connected: false });
    }
  };
});
```

---

## 4. Query Hooks Architecture (`TanStack Query`)

All REST data fetching is organized into dedicated, reusable hooks:

- `useOverviewQuery(productId, role)`: Automatically refreshes every 30s or on `issue.updated` event.
- `useIssueDetailQuery(issueId)`: Caches issue breakdown, refetches upon `survey.reply` event.
- `useReviewXRayQuery(reviewId)`: Instant cache hit once loaded.
- `useComparisonQuery(lens, a, b, metric)`: Param-driven query for statistical lens analysis.
- `useSourcesHealthQuery()`: Refreshes every 10s to monitor ingestion freshness.
