"""
PRISM Development Benchmark Evaluator
Location: benchmark/evaluate_dev_benchmark.py

Executes a debugging audit of the PRISM ML diagnostic pipeline against the
50 development benchmark records from benchmark/appliances_benchmark_v2_audited.jsonl.

Strict Invariants:
1. HOLDOUT ISOLATION: The 40 holdout records are STRICTLY excluded from evaluation.
2. PROVENANCE TRANSPARENCY: Labels are explicitly identified as 'draft_unverified'
   provisional AI annotations; results are marked PRELIMINARY.
3. DECOUPLED SIGNALS: Star ratings are treated as weak calibrating priors, NEVER ground truth.
4. METRICS REPORTING: Confusion matrices, Precision, Recall, F1, and False Negatives reported per task.
"""
import os
import sys
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone

# Ensure test fallback environment variables for settings
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/test_db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-32-chars-minimum!")

current_dir = os.path.dirname(os.path.abspath(__file__))
benchmarks_dir = current_dir
data_dir = os.path.dirname(benchmarks_dir)
hackman_dir = os.path.dirname(data_dir)
backend_dir = os.path.join(hackman_dir, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from prism_core.ml.sentiment import SentimentModel
from prism_core.ml.ambiguity import AmbiguityScorer
from prism_core.serious import assess as assess_serious
from prism_core.schemas.raw_review import RawReview, RatingPayload, ProductRef

def run_dev_evaluation(benchmark_file: str = None):
    bench_path = benchmark_file or os.path.join(current_dir, "appliances_benchmark_v2_audited.jsonl")
    if not os.path.exists(bench_path):
        raise FileNotFoundError(f"Benchmark file not found: {bench_path}")

    # Initialize PRISM ML Pipeline from official Hackman backend
    sentiment_model = SentimentModel.get_instance()
    ambiguity_scorer = AmbiguityScorer()

    # Ingest records
    dev_records = []
    holdout_records_skipped = 0

    with open(bench_path, "r", encoding="utf-8") as bf:
        for line in bf:
            if not line.strip():
                continue
            rec = json.loads(line)
            split = rec.get("split")
            status = rec.get("annotation_status")

            if split == "holdout":
                # HOLDOUT INVARIANT: Must be skipped and never evaluated
                holdout_records_skipped += 1
                assert status == "pending", f"Holdout record {rec.get('sample_id')} has non-pending status!"
                continue

            if split == "dev" and status == "draft_unverified":
                dev_records.append(rec)

    assert holdout_records_skipped == 40, f"Expected 40 skipped holdout records, found {holdout_records_skipped}"
    print("=" * 80)
    print("PRISM DEVELOPMENT BENCHMARK PRELIMINARY EVALUATION REPORT")
    print("=" * 80)
    print(f"  Target File:                   {bench_path}")
    print(f"  Evaluated Development Records: {len(dev_records)} (All labeled 'draft_unverified')")
    print(f"  Holdout Records Preserved:     {holdout_records_skipped} (Strictly Isolated & Unscored)")
    print(f"  Label Provenance:              Provisional AI-Drafted Annotations (Unconfirmed Human GT)")
    print("-" * 80)

    # Task 1: Safety Hazard Detection Tracking
    # Classes: Positive = hazard, Negative = no_hazard (unclear excluded from binary metric)
    safety_tp = 0
    safety_fp = 0
    safety_fn = 0
    safety_tn = 0
    safety_unclear_count = 0
    safety_fn_examples = []
    safety_fp_examples = []

    # Task 2: Sarcasm Detection Tracking
    # Classes: Positive = sarcasm, Negative = not_sarcasm
    sarcasm_tp = 0
    sarcasm_fp = 0
    sarcasm_fn = 0
    sarcasm_tn = 0
    sarcasm_fn_examples = []
    sarcasm_fp_examples = []

    # Task 3: Overall Review Sentiment Tracking
    # Classes: positive, negative, mixed
    sentiment_confusion = defaultdict(Counter)
    sentiment_total = 0
    sentiment_correct = 0

    now = datetime(2026, 10, 27, 10, 0, 0, tzinfo=timezone.utc)

    for item in dev_records:
        sid = item["sample_id"]
        source_id = item["source_sample_id"]
        raw_text = item.get("text", "")
        rating = float(item.get("rating", 3.0))

        raw_rev = RawReview(
            tenant_id="dev_bench",
            source_id=source_id,
            channel="amazon",
            product=ProductRef(sku=item.get("asin", "SKU_01")),
            rating=RatingPayload(value=rating),
            text=raw_text,
            reviewed_at=now,
        )

        # 1. Pipeline Execution
        safety_assessment = assess_serious(raw_rev, text=raw_text)
        pred_hazard = safety_assessment is not None

        # 2. Run Sentiment Model
        sent_res = sentiment_model.analyze_text(raw_text, rating=rating)
        pred_sentiment = sent_res["sentiment"]

        # 3. Run Ambiguity Engine
        clause_pols = [(c["polarity"], c["score"]) for c in sent_res["clauses"]]
        amb_pred = ambiguity_scorer.evaluate(
            text=raw_text,
            clause_polarities=clause_pols,
            rating=rating,
        )
        pred_sarcasm = (amb_pred["ambiguity"] == "sarcasm")


        # --- Evaluate Task 1: Safety Hazard Detection ---
        gt_safety = item["safety"]["primary_label"]
        if gt_safety == "hazard":
            if pred_hazard:
                safety_tp += 1
            else:
                safety_fn += 1
                safety_fn_examples.append({
                    "id": sid, "source_id": source_id, "text": raw_text[:100] + "...",
                    "gt_type": item["safety"].get("hazard_type"), "pred": safety_assessment
                })
        elif gt_safety == "no_hazard":
            if pred_hazard:
                safety_fp += 1
                safety_fp_examples.append({
                    "id": sid, "source_id": source_id, "text": raw_text[:100] + "...",
                    "pred_categories": safety_assessment.category if safety_assessment else None
                })
            else:
                safety_tn += 1
        elif gt_safety == "unclear":
            safety_unclear_count += 1

        # --- Evaluate Task 2: Sarcasm Detection ---
        gt_sarcasm = item["sarcasm"]["primary_label"]
        if gt_sarcasm == "sarcasm":
            if pred_sarcasm:
                sarcasm_tp += 1
            else:
                sarcasm_fn += 1
                sarcasm_fn_examples.append({
                    "id": sid, "source_id": source_id, "text": raw_text[:100] + "...",
                    "gt_evidence": item["sarcasm"].get("evidence_span"),
                    "pred_ambiguity": amb_pred.get("ambiguity")
                })
        elif gt_sarcasm == "not_sarcasm":
            if pred_sarcasm:
                sarcasm_fp += 1
                sarcasm_fp_examples.append({
                    "id": sid, "source_id": source_id, "text": raw_text[:100] + "...",
                    "pred_ambiguity": amb_pred.get("ambiguity")
                })
            else:
                sarcasm_tn += 1


        # --- Evaluate Task 3: Overall Review Sentiment ---
        gt_sent = item.get("overall_sentiment")
        if gt_sent in ["positive", "negative", "mixed"]:
            sentiment_total += 1
            sentiment_confusion[gt_sent][pred_sentiment] += 1
            if gt_sent == pred_sentiment:
                sentiment_correct += 1

    # --- Compute Task 1 Metrics ---
    s_prec = safety_tp / (safety_tp + safety_fp) if (safety_tp + safety_fp) > 0 else 0.0
    s_rec = safety_tp / (safety_tp + safety_fn) if (safety_tp + safety_fn) > 0 else 0.0
    s_f1 = (2 * s_prec * s_rec) / (s_prec + s_rec) if (s_prec + s_rec) > 0 else 0.0

    print("\n[TASK 1: SAFETY HAZARD DETECTION RESULTS (PRELIMINARY)]")
    print(f"  Evaluated Binary Cases:        {safety_tp + safety_fp + safety_fn + safety_tn} (Unclear excluded: {safety_unclear_count})")
    print("  Confusion Matrix:")
    print(f"                       Predicted Hazard    Predicted Clean")
    print(f"    Actual Hazard:          {safety_tp:3d} (TP)             {safety_fn:3d} (FN)")
    print(f"    Actual No Hazard:       {safety_fp:3d} (FP)             {safety_tn:3d} (TN)")
    print(f"  Precision:             {s_prec * 100:5.1f}%")
    print(f"  Recall:                {s_rec * 100:5.1f}%")
    print(f"  F1 Score:              {s_f1 * 100:5.1f}%")
    print(f"  False Positives (FP):  {safety_fp} (Ordinary defects correctly ignored)")
    print(f"  False Negatives (FN):  {safety_fn}")
    if safety_fn_examples:
        print("  False Negative Audit:")
        for fn in safety_fn_examples:
            print(f"    * [{fn['id']}] {fn['source_id']} ({fn['gt_type']}): \"{fn['text']}\"")
    if safety_fp_examples:
        print("  False Positive Audit:")
        for fp in safety_fp_examples:
            print(f"    * [{fp['id']}] {fp['source_id']}: \"{fp['text']}\"")

    # --- Compute Task 2 Metrics ---
    sc_prec = sarcasm_tp / (sarcasm_tp + sarcasm_fp) if (sarcasm_tp + sarcasm_fp) > 0 else 0.0
    sc_rec = sarcasm_tp / (sarcasm_tp + sarcasm_fn) if (sarcasm_tp + sarcasm_fn) > 0 else 0.0
    sc_f1 = (2 * sc_prec * sc_rec) / (sc_prec + sc_rec) if (sc_prec + sc_rec) > 0 else 0.0

    print("\n[TASK 2: SARCASM DISENTANGLEMENT RESULTS (PRELIMINARY)]")
    print(f"  Evaluated Cases:               {sarcasm_tp + sarcasm_fp + sarcasm_fn + sarcasm_tn}")
    print("  Confusion Matrix:")
    print(f"                       Predicted Sarcasm   Predicted Sincere/Other")
    print(f"    Actual Sarcasm:         {sarcasm_tp:3d} (TP)             {sarcasm_fn:3d} (FN)")
    print(f"    Actual Not Sarcasm:     {sarcasm_fp:3d} (FP)             {sarcasm_tn:3d} (TN)")
    print(f"  Precision:             {sc_prec * 100:5.1f}%")
    print(f"  Recall:                {sc_rec * 100:5.1f}%")
    print(f"  F1 Score:              {sc_f1 * 100:5.1f}%")
    print(f"  False Negatives (FN):  {sarcasm_fn}")
    if sarcasm_fn_examples:
        print("  False Negative Audit:")
        for fn in sarcasm_fn_examples:
            print(f"    * [{fn['id']}] {fn['source_id']}: Span: \"{fn['gt_evidence']}\" | Pred: {fn['pred_ambiguity']}")
    if sarcasm_fp_examples:
        print("  False Positive Audit:")
        for fp in sarcasm_fp_examples:
            print(f"    * [{fp['id']}] {fp['source_id']}: \"{fp['text']}\"")

    # --- Compute Task 3 Metrics ---
    sent_acc = sentiment_correct / sentiment_total if sentiment_total > 0 else 0.0
    print("\n[TASK 3: REVIEW-LEVEL SENTIMENT CLASSIFICATION (PRELIMINARY)]")
    print(f"  Evaluated Cases:               {sentiment_total}")
    print(f"  Overall Exact Agreement:       {sentiment_correct} / {sentiment_total} ({sent_acc * 100:.1f}%)")
    print("  Multi-Class Confusion Matrix (Rows = Ground Truth, Columns = Predicted):")
    print("  " + f"{'':<12} | {'positive':<10} | {'negative':<10} | {'neutral':<10}")
    print("  " + "-" * 48)
    for row_cls in ["positive", "negative", "mixed"]:
        c_pos = sentiment_confusion[row_cls].get("positive", 0)
        c_neg = sentiment_confusion[row_cls].get("negative", 0)
        c_neu = sentiment_confusion[row_cls].get("neutral", 0)
        print(f"  {row_cls:<12} | {c_pos:<10} | {c_neg:<10} | {c_neu:<10}")

    print("\n" + "=" * 80)
    print("PRELIMINARY AUDIT SUMMARY & SCIENTIFIC GOVERNANCE NOTICE")
    print("=" * 80)
    print("1. PRELIMINARY NOTICE: These metrics represent debugging diagnostic performance against")
    print("   the 50 development reviews only. They must be marked as preliminary because:")
    print("   - Sample size is limited (N = 50 development reviews).")
    print("   - Labels are 'draft_unverified' AI-synthesized annotations rather than confirmed")
    print("     independent human ground truth.")
    print("2. HOLDOUT ISOLATION: The 40 holdout reviews were NOT evaluated, scored, or tuned against.")
    print("   Holdout performance will only be reported after blind independent human annotation.")
    print("3. DECOUPLED SIGNALS: Amazon star ratings were decoupled and not used as ground truth.")
    print("=" * 80)

if __name__ == "__main__":
    run_dev_evaluation()
