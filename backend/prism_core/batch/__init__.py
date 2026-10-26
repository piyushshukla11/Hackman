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


def infer(review: NormalisedReview, raw: RawReview | None = None) -> BatchInference:
    """
    Public entrypoint for L3 Batch Inference ladder.
    Returns BatchInference object with method, confidence, and identified batch.
    """
    if raw is None:
        return BatchInference(batch_id=None, batch_method="B4", batch_conf=0.30, pooled=True)

    # ── B0: Explicit Batch Code in Payload ────────────────────────────────────────
    if raw.batch_code and raw.batch_code.strip():
        return BatchInference(
            batch_id=raw.batch_code.strip(),
            batch_method="B0",
            batch_conf=1.00,
            pooled=False,
        )

    # ── B1: OCR Serial Label Text in Media Items ──────────────────────────────────
    for m in raw.media:
        if m.ocr_text and m.ocr_text.strip():
            match = BATCH_CODE_REGEX.search(m.ocr_text)
            if match:
                return BatchInference(
                    batch_id=match.group(0).upper(),
                    batch_method="B1",
                    batch_conf=0.85,
                    pooled=False,
                )

    # Check text for inline mentioned batch codes
    full_text = (review.text_original or "") + " " + (review.text_en or "")
    text_match = BATCH_CODE_REGEX.search(full_text)
    if text_match:
        return BatchInference(
            batch_id=text_match.group(0).upper(),
            batch_method="B1",
            batch_conf=0.85,
            pooled=False,
        )

    # ── B2: Warehouse + Dispatch Date Lookup ─────────────────────────────────────
    if raw.order and raw.order.dispatch_date and raw.order.warehouse:
        dispatch_iso = raw.order.dispatch_date.isoformat()
        wh = raw.order.warehouse.strip().upper()
        inferred_code = f"BATCH-WH-{wh}-{dispatch_iso[:7]}"
        return BatchInference(
            batch_id=inferred_code,
            batch_method="B2",
            batch_conf=0.70,
            pooled=False,
        )

    # ── B3: Purchase Date Cohort Window ──────────────────────────────────────────
    if raw.order and raw.order.purchase_date:
        p_iso = raw.order.purchase_date.isoformat()
        inferred_code = f"COHORT-PURCHASE-{p_iso[:7]}"
        return BatchInference(
            batch_id=inferred_code,
            batch_method="B3",
            batch_conf=0.50,
            pooled=True,
        )

    # ── B4: Review Date Submission Window ────────────────────────────────────────
    r_iso = raw.reviewed_at.date().isoformat()
    inferred_code = f"COHORT-REVIEW-{r_iso[:7]}"
    return BatchInference(
        batch_id=inferred_code,
        batch_method="B4",
        batch_conf=0.30,
        pooled=True,
    )
