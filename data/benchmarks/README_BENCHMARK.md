# PRISM Forensic Evaluation Benchmark & Provenance Audit

> **Corpus**: Amazon Reviews'23 (Appliances Category)  
> **Host Institution**: UCSD McAuley Lab (*Hou et al., arXiv:2403.03952*, 2024)  
> **Audited Benchmark Path**: [`appliances_benchmark_v2_audited.jsonl`](file:///d:/neo/hachathon/hack%20malenadu/prism/PRISM/benchmark/appliances_benchmark_v2_audited.jsonl)  
> **Legacy Initial Benchmark**: [`appliances_ground_truth_benchmark.jsonl`](file:///d:/neo/hachathon/hack%20malenadu/prism/PRISM/benchmark/appliances_ground_truth_benchmark.jsonl)  
> **Annotation Protocol**: [`ANNOTATION_GUIDE.md`](file:///d:/neo/hachathon/hack%20malenadu/prism/PRISM/benchmark/ANNOTATION_GUIDE.md)  
> **Validation Utility**: [`validate_benchmark.py`](file:///d:/neo/hachathon/hack%20malenadu/prism/PRISM/benchmark/validate_benchmark.py)  
> **Dev Evaluation Script**: [`evaluate_dev_benchmark.py`](file:///d:/neo/hachathon/hack%20malenadu/prism/PRISM/benchmark/evaluate_dev_benchmark.py)  
> **Version**: 2.0.0 (Audited)  
> **Status**: Development `draft_unverified` (50) + `pending` (50: 10 dev, 40 holdout)  

---

## 1. Provenance Audit Findings

A rigorous audit of the benchmark files, repository logs, and annotation provenance was conducted prior to model scoring:

1. **Absence of Real Human Study Records**:
   - The initial 50 completed development annotations contained synthetic role tags (`annotator_1`, `annotator_2`, `lead_adjudicator`) produced programmatically during drafting.
   - The repository contains no independent human annotator session logs, signed review sheets, or multi-annotator platform telemetry.
   - **Audit Action**: Per scientific governance standards, these 50 development records have been formally relabeled as **`draft_unverified`** in [`appliances_benchmark_v2_audited.jsonl`](file:///d:/neo/hachathon/hack%20malenadu/prism/PRISM/benchmark/appliances_benchmark_v2_audited.jsonl). They are **not** claimed as confirmed human ground truth.
2. **Holdout Blind Isolation**:
   - The **40 holdout reviews** are strictly preserved with **`annotation_status: "pending"`**.
   - No holdout labels have been revealed or generated using model predictions.
   - Holdout reviews are excluded from model tuning, optimization, and preliminary scoring.
3. **Availability of Human Reviewers**:
   - Real human reviewers were not available during this audit turn.
   - Consequently, holdout labels remain `pending`. Independent human annotation using [`ANNOTATION_GUIDE.md`](file:///d:/neo/hachathon/hack%20malenadu/prism/PRISM/benchmark/ANNOTATION_GUIDE.md) is still required prior to official holdout benchmarking.
4. **Automated Validation Limits**:
   - Automated validation scripts ([`validate_benchmark.py`](file:///d:/neo/hachathon/hack%20malenadu/prism/PRISM/benchmark/validate_benchmark.py)) verify JSON syntax, source text identity, allowed vocabulary, and exact evidence-span containment.
   - **Automated validation cannot prove that a label is empirically correct or that named annotators were real human beings.**

---

## 2. Sampling Methodology & Disjoint Product Split

- **Sampling Technique**: Stratified sampling across all five star ratings (1.0★ through 5.0★) with uniform coverage of review lengths and appliance subcategories.
- **Random Seed**: `20261026` (guarantees deterministic reproducibility).
- **Product Partitioning Invariant**: Partitioned strictly by **`parent_asin`** (parent product SKU):
  $$\text{ParentASINs}(\text{dev}) \cap \text{ParentASINs}(\text{holdout}) = \emptyset$$
- **Split Breakdown**:
  - **Development Split (`dev`)**: 60 reviews across 50 distinct products.
    - 50 reviews labeled **`draft_unverified`** (provisional AI draft annotations for internal debugging).
    - 10 reviews labeled **`pending`**.
  - **Holdout Split (`holdout`)**: 40 reviews across 40 disjoint products.
    - All 40 reviews labeled **`pending`** (isolated for future blind evaluation).

---

## 3. Preliminary Debugging Results (50 Development Records Only)

The existing PRISM ML pipeline was evaluated against the 50 `draft_unverified` development records using [`evaluate_dev_benchmark.py`](file:///d:/neo/hachathon/hack%20malenadu/prism/PRISM/benchmark/evaluate_dev_benchmark.py). 

> **Important Notice**: These results are **strictly preliminary** for debugging purposes. Sample size is limited ($N = 50$), and labels are unverified drafts rather than confirmed human ground truth. The 40 holdout reviews were **not scored**.

### 3.1 Task 1: Safety Hazard Detection (Preliminary)
- **Binary Evaluated Cases**: 49 (1 `unclear` excluded)
- **Confusion Matrix**:
  ```
                       Predicted Hazard    Predicted Clean
    Actual Hazard:            2 (TP)              10 (FN)
    Actual No Hazard:         0 (FP)              37 (TN)
  ```
- **Precision**: **100.0%** (0 false alarms; water leaks, melting ice, motor noise correctly ignored)
- **Recall**: **16.7%** (2 TP / 12 Actual Hazards)
- **F1 Score**: **28.6%**
- **False Negative Analysis**: The 10 false negatives occurred on complex multi-paragraph reviews describing indirect hazards (e.g., sister burning counter, uninsulated oven door reaching 200°F, cigarette lighter plug burning fingers, microwave fire, heating element burning hole through dishwasher tub).

### 3.2 Task 2: Sarcasm Disentanglement (Preliminary)
- **Evaluated Cases**: 50
- **Confusion Matrix**:
  ```
                       Predicted Sarcasm   Predicted Sincere/Other
    Actual Sarcasm:           0 (TP)               5 (FN)
    Actual Not Sarcasm:       0 (FP)              45 (TN)
  ```
- **Precision**: **0.0%**, **Recall**: **0.0%**, **F1 Score**: **0.0%**
- **False Negative Analysis**: All 5 draft sarcastic reviews (*"great job amazon"*, *"filter does make a great frizzbee"*, *"delivered by Airmail but without the benefit of a parachute"*, *"quality control isn't doing a great job"*, *"if someone doesn't cook and only needs it to look good"*) were classified as `sincere` or `mixed`. Without explicit irony markers (such as sarcastic emojis or explicit quotation cues), the deterministic pass defaulted to sincere criticism.

### 3.3 Task 3: Review-Level Sentiment Classification (Preliminary)
- **Evaluated Cases**: 50
- **Exact Agreement**: 14 / 50 (**28.0%**)
- **Multi-Class Confusion Matrix**:
  | Ground Truth | Predicted Positive | Predicted Negative | Predicted Neutral |
  | :--- | :---: | :---: | :---: |
  | **positive** (15) | **8** | 0 | 7 |
  | **negative** (26) | 5 | **6** | 15 |
  | **mixed** (9) | 3 | 1 | 5 |
- **Diagnostic Finding**: 27 out of 50 reviews were classified as `neutral` due to the conservative sentiment thresholding band.

---

## 4. Governance & Usage Protocol

1. **Do not claim benchmark accuracy as proof of production readiness**: A 50-review development set with draft labels cannot establish statistical bounds for production deployment.
2. **Holdout Evaluation**: Formal holdout evaluation must only occur after real human annotators complete independent annotation and adjudication of the 40 holdout records.
3. **Decoupled Star Ratings**: Star ratings must continue to be treated as user-supplied weak priors ($0.15$ weight), never as ground truth for safety, sarcasm, or sentiment.
