"""
prism_core/batch/__init__.py

L3 Batch Inference Ladder B0 through B4:
B0: Direct batch code in review metadata (conf 1.00)
B1: Serial label OCR text from product photos (conf 0.85)
B2: Registry dispatch date + warehouse lookup (conf 0.70)
B3: Purchase date cohort window (conf 0.50)
B4: Review date submission cohort window (conf 0.30)
"""
from __future__ import annotations

import re
from typing import Literal
from prism_core.schemas.clean import NormalisedReview
from prism_core.schemas.raw_review import RawReview
from prism_core.schemas.understand import BatchInference

BATCH_CODE_REGEX = re.compile(r"\b(BATCH|LOT|BCH)[-_]?[0-9]{4}[-_]?[A-Z0-9]{2,}\b", re.IGNORECASE)
TEXT_BATCH_REGEX = re.compile(r"\bbatch\s+([A-Za-z0-9\-]+)\b", re.IGNORECASE)


def infer(review: Any = None, raw: Any = None) -> BatchInference:
    """
    Public entrypoint for L3 Batch Inference ladder.
    Returns BatchInference object with method, confidence, and identified batch.
    """
    actual_raw: Any = None
    actual_norm: Any = None

    if review is not None and (hasattr(review, "batch_code") or hasattr(review, "order")):
        actual_raw = review
        actual_norm = raw
    elif raw is not None and (hasattr(raw, "batch_code") or hasattr(raw, "order")):
        actual_raw = raw
        actual_norm = review
    else:
        actual_norm = review
        actual_raw = raw

    if actual_raw is None:
        return BatchInference(batch_id=None, batch_method="B4", batch_conf=0.30, pooled=True)

    # ── B0: Explicit Batch Code in Payload or Text ────────────────────────────────
    batch_code = getattr(actual_raw, "batch_code", None)
    if batch_code and str(batch_code).strip():
        return BatchInference(
            batch_id=str(batch_code).strip(),
            batch_method="B0",
            batch_conf=1.00,
            pooled=False,
        )

    full_text = ""
    if actual_raw:
        full_text += " " + (getattr(actual_raw, "text", None) or "")
    if actual_norm:
        full_text += " " + (getattr(actual_norm, "text_original", None) or "") + " " + (getattr(actual_norm, "text_en", None) or "")

    text_batch_match = TEXT_BATCH_REGEX.search(full_text)
    if text_batch_match:
        return BatchInference(
            batch_id=text_batch_match.group(1),
            batch_method="B0",
            batch_conf=1.00,
            pooled=False,
        )

    # ── B1: OCR Serial Label Text in Media Items ──────────────────────────────────
    for m in getattr(actual_raw, "media", []) or []:
        ocr_text = getattr(m, "ocr_text", None)
        if ocr_text and ocr_text.strip():
            match = BATCH_CODE_REGEX.search(ocr_text)
            if match:
                return BatchInference(
                    batch_id=match.group(0).upper(),
                    batch_method="B1",
                    batch_conf=0.85,
                    pooled=False,
                )

    code_match = BATCH_CODE_REGEX.search(full_text)
    if code_match:
        return BatchInference(
            batch_id=code_match.group(0).upper(),
            batch_method="B1",
            batch_conf=0.85,
            pooled=False,
        )

    # ── B2: Warehouse + Dispatch Date Lookup ─────────────────────────────────────
    order = getattr(actual_raw, "order", None)
    order_dict = order if isinstance(order, dict) else (order.__dict__ if hasattr(order, "__dict__") else {})
    warehouse = getattr(order, "warehouse", None) or order_dict.get("warehouse")
    dispatch_date = getattr(order, "dispatch_date", None) or order_dict.get("dispatch_date")

    if dispatch_date and warehouse:
        dispatch_iso = dispatch_date.isoformat() if hasattr(dispatch_date, "isoformat") else str(dispatch_date)
        wh = str(warehouse).strip().upper()
        inferred_code = f"BATCH-WH-{wh}-{dispatch_iso[:7]}"
        return BatchInference(
            batch_id=inferred_code,
            batch_method="B2",
            batch_conf=0.70,
            pooled=False,
        )

    # ── B3: Purchase Date Cohort Window ──────────────────────────────────────────
    purchase_date = getattr(order, "purchase_date", None) or order_dict.get("purchase_date")
    if purchase_date:
        p_day = getattr(purchase_date, "day", 1)
        p_month = getattr(purchase_date, "month", 1)
        p_year = getattr(purchase_date, "year", 2026)
        channel = getattr(actual_raw, "channel", "COHORT") or "COHORT"
        fn = "FN1" if p_day <= 15 else "FN2"
        inferred_code = f"COHORT_{channel.upper()}_{p_year}_{p_month:02d}_{fn}"
        return BatchInference(
            batch_id=inferred_code,
            batch_method="B3",
            batch_conf=0.50,
            pooled=True,
        )

    # ── B4: Review Date Submission Window ────────────────────────────────────────
    reviewed_at = getattr(actual_raw, "reviewed_at", None)
    if reviewed_at:
        r_iso = reviewed_at.date().isoformat() if hasattr(reviewed_at, "date") else str(reviewed_at)
        inferred_code = f"COHORT-REVIEW-{r_iso[:7]}"
    else:
        inferred_code = "COHORT-REVIEW-UNKNOWN"

    return BatchInference(
        batch_id=inferred_code,
        batch_method="B4",
        batch_conf=0.30,
        pooled=True,
    )


infer_batch = infer

