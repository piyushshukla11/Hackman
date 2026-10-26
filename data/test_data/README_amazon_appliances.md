# Amazon Reviews'23 — Appliances Test Dataset (20k Sample)

> **Dataset Name**: Amazon Reviews'23 (Appliances Category)  
> **Source**: UCSD McAuley Lab (University of California San Diego)  
> **Source URL**: https://amazon-reviews-2023.github.io/  
> **Hugging Face Repository**: https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023  
> **Academic Citation**: Hou et al., *"Bridging Language and Items for Retrieval and Recommendation"*, arXiv:2403.03952 (2024).  
> **Download Date**: 2026-10-26  
> **Notice**: This is a public academic research dataset curated and hosted by UC San Diego; it is **not an official Amazon release**.

---

## 1. Dataset Overview

This dataset is a reproducible, rating-balanced sample of **20,000 customer reviews** extracted from the **Appliances** category of the Amazon Reviews'23 corpus.

### Target & Actual Sample Counts

The sampling target was a balanced collection of **4,000 reviews per star rating** (1.0 to 5.0):

| Rating | Target Count | Actual Sampled Count | Percentage |
| :---: | :---: | :---: | :---: |
| **1.0 ★** | 4,000 | 4,000 | 20.0% |
| **2.0 ★** | 4,000 | 4,000 | 20.0% |
| **3.0 ★** | 4,000 | 4,000 | 20.0% |
| **4.0 ★** | 4,000 | 4,000 | 20.0% |
| **5.0 ★** | 4,000 | 4,000 | 20.0% |
| **TOTAL** | **20,000** | **20,000** | **100.0%** |

- **Total Reviews in Raw Appliances File**: 2,128,605 reviews
- **Sampling Ratio**: 0.94% of category corpus

---

## 2. Sampling Methodology

- **Sampling Technique**: Stratified random sampling across star ratings with uniform distribution.
- **Random Seed**: `20261026` (fixed seed ensures exact byte-level reproducibility).
- **Integrity Verification**: The source archive (`Appliances.jsonl`, 929,451,412 bytes) was verified against the official Git LFS SHA-256 checksum (`d9dd03aa9be0c8e6fea66d8ce99a7e5b359e272d6323186c1aa80f6d36af1dab`) prior to parsing.
- **Anonymization**: In compliance with privacy guidelines, raw `user_id` values were stripped and replaced with stable, 16-character SHA-256 hashes (`sha256:<hash>`) to enable reviewer-grouping evaluations without exposing raw user IDs.

---

## 3. Schema & Field Definitions

Each line in `amazon_appliances_20k.jsonl` is a valid, standalone UTF-8 JSON object:

| Field | Type | Description |
| :--- | :--- | :--- |
| `sample_id` | `string` | Unique sample identifier (`AMZ_APP_00001` to `AMZ_APP_20000`). |
| `rating` | `float` | Customer star rating (1.0, 2.0, 3.0, 4.0, 5.0). |
| `title` | `string` | Review heading or title (as provided by reviewer). |
| `text` | `string` | Full customer review body text. |
| `verified_purchase` | `boolean` | `true` if review is marked as an Amazon Verified Purchase. |
| `helpful_vote` | `integer` | Count of helpful votes received from other customers. |
| `timestamp` | `integer` | Submission timestamp in Unix epoch milliseconds. |
| `asin` | `string` | Amazon Standard Identification Number (SKU identifier). |
| `parent_asin` | `string` | Parent product ASIN for multi-variant products. |
| `user_id` | `string` | Anonymized reviewer hash (`sha256:7f9a...`). |
| `category` | `string` | Product category (`"Appliances"`). |
| `source` | `string` | Dataset provenance (`"Amazon Reviews'23 (UCSD McAuley Lab)"`). |

### Sample Record
```json
{
  "sample_id": "AMZ_APP_00001",
  "rating": 1.0,
  "title": "Terrible quality, broke after 2 weeks",
  "text": "The motor burned out during regular use. Completely useless.",
  "verified_purchase": true,
  "helpful_vote": 3,
  "timestamp": 1582412800000,
  "asin": "B01N0TQ0OH",
  "parent_asin": "B01N0TQ0OH",
  "user_id": "sha256:8b4f2c1e90d3a7b5",
  "category": "Appliances",
  "source": "Amazon Reviews'23 (UCSD McAuley Lab)"
}
```

---

## 4. Methodological Cautions & Usage Notes for PRISM ML

1. **Weak Sentiment Signal**:
   Customer star ratings represent self-reported, subjective opinions and **must not be treated as ground truth** for PRISM's automated predictions. A 5-star review may contain sarcastic complaints, and a 1-star review may praise the hardware while complaining about courier delays.
2. **No Ground Truth for Forensic Tasks**:
   This dataset contains no human-verified labels for:
   - Component-level feature sentiment (e.g. thermostat vs motor vs gasket)
   - Sarcasm or irony
   - Manufacturing batch defects or warehouse routing
   - Safety hazard severity (fire, electric shock, chemical leak)
   - Bot collusion or duplicate coordination
3. **Model Evaluation Purpose**:
   This dataset is designed for **high-volume throughput testing, schema validation, distributional auditing, and stress testing** PRISM's pipeline under real-world noisy e-commerce conditions. It does not constitute proof of forensic prediction accuracy.

---

## 5. File Locations

- **Sampled Dataset**: `test_data/amazon_appliances_20k.jsonl` (and `ml_tests/amazon_appliances_20k.jsonl`)
- **Documentation**: `test_data/README_amazon_appliances.md` (and `ml_tests/README_amazon_appliances.md`)
