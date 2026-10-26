# PRISM ML Service Integration Guide for Backend & Frontend Teams

> **Audience**: Full-Stack, Backend (Node.js/Go/Python/Java), and Frontend (React/Next.js/Vue) Engineers  
> **Service Location**: `ml_service/` (Runs on `http://127.0.0.1:8000`)  
> **API Docs (Swagger UI)**: `http://127.0.0.1:8000/docs`  
> **ReDoc**: `http://127.0.0.1:8000/redoc`  

---

## 1. Quick Start

### Starting the ML Microservice
In PowerShell from workspace root:
```powershell
.\start_ml.ps1
```
The service launches on `http://127.0.0.1:8000` with hot-reloading enabled.

---

## 2. Integration Architecture

The ML service is designed to be **completely decoupled and universal**:
1. **Any Backend**: Node.js/Express, Go, Python, Java, or Ruby can call the REST API via HTTP JSON.
2. **Any Frontend**: React, Vite, Next.js, Vue, or mobile apps can call endpoints directly (CORS is globally enabled for `*`).
3. **Clients Included**:
   - JavaScript Client: `ml_service/clients/mlClient.js` (Zero dependencies, works in Node & Browser)
   - TypeScript Client: `ml_service/clients/mlClient.ts` (Full types & autocomplete)

---

## 3. Recommended Integration Patterns

### Pattern A: All-in-One Review Processing (Highest Efficiency)
Instead of making 6 round-trips over the network for a single review, call the unified pipeline:

#### Endpoint: `POST /ml/pipeline/process-review`
```json
{
  "id": "rev_101",
  "text": "The bass is deep and clear, but the outer packaging was crushed.",
  "rating": 4.0,
  "category": "headphones",
  "verified_purchase": true,
  "explicit_batch_code": "B-0716",
  "dispatch_date": "2026-07-10",
  "warehouse": "W2"
}
```

#### Output (Unified JSON):
```json
{
  "id": "rev_101",
  "raw_text": "The bass is deep and clear, but the outer packaging was crushed.",
  "clean_text": "The bass is deep and clear, but the outer packaging was crushed.",
  "language": {
    "lang": "en",
    "script": "Latin",
    "is_hinglish": false,
    "emojis": []
  },
  "pii_masked": false,
  "trust": {
    "verdict": "clean",
    "text_status": "clean",
    "rating_status": "counted",
    "trust_score": 0.95
  },
  "safety": {
    "is_serious": false
  },
  "features": [
    {
      "feature": "sound_quality",
      "polarity": "positive",
      "score": 0.55,
      "source_clause": "The bass is deep and clear"
    },
    {
      "feature": "packaging",
      "polarity": "negative",
      "score": -0.60,
      "source_clause": "outer packaging was crushed"
    }
  ],
  "ambiguity": {
    "type": "none",
    "confidence_multiplier": 1.0,
    "signals": [],
    "explanation": null
  },
  "batch": {
    "batch_id": "batch_0716",
    "batch_method": "B0_explicit",
    "batch_conf": 1.0
  },
  "embedding": [0.034, -0.012, 0.089, "... 384 dimensions ..."]
}
```

---

### Pattern B: High-Throughput Batch Processing (Database Ingestion / ETL)
When importing hundreds of reviews from CSV, Amazon scraper, or Flipkart API, use:

#### Endpoint: `POST /ml/pipeline/process-batch`
```json
{
  "category": "headphones",
  "reviews": [
    { "id": "r1", "text": "Super sound quality!", "rating": 5.0, "verified_purchase": true },
    { "id": "r2", "text": "Battery died in 2 hours.", "rating": 1.0, "explicit_batch_code": "B-0716" }
  ]
}
```
**Benefits**:
- Embeddings are vectorized in batch via PyTorch CPU for 5x to 10x faster inference.
- Eliminates HTTP connection handshake overhead.

---

### Pattern C: Modular Microservice Calls
If your backend already has custom orchestration logic, you can call any individual stage independently:

| Use Case | Endpoint | Request Payload | Response Key Highlights |
| :--- | :--- | :--- | :--- |
| **Language & PII** | `POST /ml/normalize` | `{"text": "..."}` | `clean_text`, `lang`, `script`, `emojis`, `pii_masked` |
| **Trust Evaluation** | `POST /ml/trust` | `{"review_text": "...", "verified_purchase": true}` | `verdict`, `text_status`, `rating_status`, `trust_score` |
| **Feature Extraction** | `POST /ml/extract` | `{"text": "...", "category": "headphones", "rating": 4.0}` | `features`, `ambiguity`, `confidence_multiplier`, `embedding` |
| **Batch Identification**| `POST /ml/batch-infer` | `{"explicit_batch_code": "B-0716", "dispatch_date": "..."}` | `batch_id`, `batch_method`, `batch_conf` |
| **Safety Alarms** | `POST /ml/serious` | `{"text": "...", "trust_verdict": "clean"}` | `is_serious`, `severity`, `alert_required`, `unverified` |
| **Dense Vectors** | `POST /ml/embed` | `{"texts": ["..."], "kind": "passage"}` | `embeddings` (array of 384-d floats) |
| **Graph Clusters** | `POST /ml/graph-rebuild` | `{"mentions": [...], "product_baseline_neg_rate": 0.15}` | `clusters`, `issue_type` (`isolated`, `batch`, `systemic`) |
| **Confidence Score** | `POST /ml/confidence` | `{"cluster": {...}, "total_product_reviews": 100}` | `confidence` ($0.0 - 1.0$), `confidence_parts` waterfall |
| **Statistical Compare**| `POST /ml/compare` | `{"lens": "version", "group_a": {...}, "group_b": {...}}` | `verdict`, `delta`, `p_value`, `ci_lower`, `ci_upper` |
| **Diagnostic Survey** | `POST /ml/survey/draft` | `{"product_name": "...", "feature": "...", "issue_type": "..."}` | `questions` (targeted yes/no follow-ups) |
| **Survey Ingestion** | `POST /ml/survey/ingest` | `{"questions": [...], "answers": {...}, "current_confidence": 0.65}`| `updated_confidence`, `survey_delta` |

---

## 4. Code Examples for Any Stack

### Node.js / Express Example
```javascript
const PRISMMLClient = require('../ml_service/clients/mlClient');
const ml = new PRISMMLClient(process.env.ML_SERVICE_URL || 'http://127.0.0.1:8000');

// Inside your Express review ingestion handler:
app.post('/api/reviews', async (req, res) => {
  try {
    const mlResult = await ml.processReview({
      id: req.body.id,
      text: req.body.text,
      rating: req.body.rating,
      category: req.body.category,
      verified_purchase: req.body.verified_purchase,
      explicit_batch_code: req.body.batch_code,
    });

    // Check for high-liability safety hazards immediately:
    if (mlResult.safety?.alert_required) {
      notifyProductSafetyTeam(mlResult);
    }

    // Save enriched result to your database
    await db.reviews.insert(mlResult);
    res.json({ success: true, data: mlResult });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});
```

### React / Frontend Direct Example
```tsx
import { useEffect, useState } from 'react';
import { PRISMMLClientTS } from '../../ml_service/clients/mlClient';

const mlClient = new PRISMMLClientTS('http://127.0.0.1:8000');

export function LiveReviewAuditor() {
  const [text, setText] = useState('');
  const [analysis, setAnalysis] = useState(null);

  const analyze = async () => {
    const result = await mlClient.processReview({
      text,
      category: 'headphones',
      rating: 4.0
    });
    setAnalysis(result);
  };

  return (
    <div>
      <textarea value={text} onChange={(e) => setText(e.target.value)} />
      <button onClick={analyze}>Analyze Review</button>
      {analysis && (
        <div>
          <p>Trust Score: {analysis.trust.trust_score}</p>
          <p>Language: {analysis.language.lang}</p>
          <p>Features Found: {analysis.features.length}</p>
        </div>
      )}
    </div>
  );
}
```

### Python / FastAPI Backend Example
```python
import httpx

ML_URL = "http://127.0.0.1:8000"

async def enrich_review(review_data: dict) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{ML_URL}/ml/pipeline/process-review", json=review_data, timeout=10.0)
        resp.raise_for_status()
        return resp.json()
```

---

## 5. Error Handling & Performance Recommendations
1. **Timeouts**: Set an HTTP client timeout of at least **10 seconds** for single reviews and **30 seconds** for batches $\ge 100$.
2. **Status Codes**:
   - `200 OK`: Successful inference with JSON output.
   - `422 Unprocessable Entity`: Request body is missing required fields (e.g., missing `text`).
   - `500 Internal Error`: Check ML service console logs.
3. **Decoupled Star Ratings**: Remember that clean short reviews (`"Good!"`) have `text_status = 'rejected_short'` (omitted from feature graphs) but **`rating_status = 'counted'`** (should be included in product aggregate star calculations).
