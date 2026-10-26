"""
workflows/tasks/process_review.py

Render Workflows Task: process_review(raw_id: str)
Fans out from Ingest Gateway. Durably executes the canonical review pipeline:
1. Normalise (L2 Language & translation)
2. Trust (L2 Trust Cascade G1-G6)
3. Understand (L3 Feature Extraction & Ambiguity)
4. Batch Infer (L3 Batch Inference ladder B0-B4)
5. Serious Assessment (L3 Safety risks)

Emits real-time SSE events via events.emit() so judges can observe task execution live in Prism Stream.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prism_core.batch import infer as infer_batch
from prism_core.db.base import get_sessionmaker
from prism_core.db.models import Product, RawReview as RawReviewModel, Review, ReviewFeature, SeriousComplaint, TrustGateLog
from prism_core.events import emit
from prism_core.extract import analyse as extract_analyse
from prism_core.language import normalise as normalise_lang
from prism_core.schemas.raw_review import RawReview
from prism_core.trust import score as score_trust


async def execute_process_review(raw_id: str, attempt: int = 1) -> str:
    """
    Pure Python task implementation of process_review pipeline.
    Wrapped by Render Workflows worker.
    """
    sessionmaker = get_sessionmaker()
    t_start = time.perf_counter()

    async with sessionmaker() as session:
        # Fetch RawReview
        raw_model = await session.get(RawReviewModel, raw_id)
        if not raw_model:
            raise ValueError(f"RawReview {raw_id} not found")

        tenant_id = raw_model.tenant_id
        envelope = RawReview.model_validate(raw_model.payload)
        run_id = f"proc_{raw_id[:8]}"

        # Resolve product_id
        product_sku = envelope.product.sku or envelope.product.external_id or ""
        prod_stmt = select(Product).where(Product.tenant_id == tenant_id, Product.name.ilike(f"%{product_sku}%"))
        prod = (await session.execute(prod_stmt)).scalar_one_or_none()
        product_id = prod.id if prod else f"prod_{product_sku}"
        custom_features = prod.custom_features if prod else []

        # ── STAGE 1: Normalise Language ──────────────────────────────────────────
        s1_start = time.perf_counter()
        await emit("normalise", "started", run_id, tenant_id=tenant_id, review_id=raw_id, attempt=attempt, session=session)
        norm = await normalise_lang(envelope)
        s1_dur = int((time.perf_counter() - s1_start) * 1000)
        await emit("normalise", "done", run_id, tenant_id=tenant_id, review_id=raw_id, attempt=attempt, duration_ms=s1_dur, session=session)

        # ── STAGE 2: Trust Cascade ───────────────────────────────────────────────
        s2_start = time.perf_counter()
        await emit("trust", "started", run_id, tenant_id=tenant_id, review_id=raw_id, attempt=attempt, session=session)
        trust_verdict = score_trust(norm, raw=envelope)
        s2_dur = int((time.perf_counter() - s2_start) * 1000)
        await emit("trust", "done", run_id, tenant_id=tenant_id, review_id=raw_id, attempt=attempt, duration_ms=s2_dur, session=session,
                   detail={"verdict": trust_verdict.verdict, "trust_score": trust_verdict.trust_score})

        # ── STAGE 3: Extract Features & Ambiguity ────────────────────────────────
        s3_start = time.perf_counter()
        await emit("understand", "started", run_id, tenant_id=tenant_id, review_id=raw_id, attempt=attempt, session=session)
        analysis = extract_analyse(norm, product_id=product_id, custom_features=custom_features, user_rating=envelope.rating.value)
        s3_dur = int((time.perf_counter() - s3_start) * 1000)
        await emit("understand", "done", run_id, tenant_id=tenant_id, review_id=raw_id, attempt=attempt, duration_ms=s3_dur, session=session,
                   detail={"features_found": len(analysis.features)})

        # ── STAGE 4: Batch Inference ─────────────────────────────────────────────
        s4_start = time.perf_counter()
        await emit("batch_infer", "started", run_id, tenant_id=tenant_id, review_id=raw_id, attempt=attempt, session=session)
        batch_inf = infer_batch(norm, raw=envelope)
        s4_dur = int((time.perf_counter() - s4_start) * 1000)
        await emit("batch_infer", "done", run_id, tenant_id=tenant_id, review_id=raw_id, attempt=attempt, duration_ms=s4_dur, session=session,
                   detail={"batch_id": batch_inf.batch_id, "method": batch_inf.batch_method})

        # ── PERSISTENCE: Save Canonical Review Record ────────────────────────────
        review_record = Review(
            raw_id=raw_id,
            tenant_id=tenant_id,
            product_id=product_id,
            source_id=envelope.source_id,
            channel=envelope.channel,
            rating=envelope.rating.value,
            rating_raw=str(envelope.rating.raw_value),
            rating_scale=envelope.rating.scale,
            text_original=norm.text_original,
            text_en=norm.text_en,
            lang=norm.lang,
            script=norm.script,
            reviewed_at=envelope.reviewed_at,
            purchase_date=envelope.order.purchase_date if envelope.order else None,
            dispatch_date=envelope.order.dispatch_date if envelope.order else None,
            warehouse=envelope.order.warehouse if envelope.order else None,
            seller=envelope.order.seller if envelope.order else None,
            verified_purchase=envelope.author.verified_buyer,
            author_hash=envelope.author.id_hash,
            media=[m.model_dump(mode="json") for m in envelope.media],
            batch_id=batch_inf.batch_id,
            batch_method=batch_inf.batch_method,
            batch_conf=batch_inf.batch_conf,
            version_id=batch_inf.version_id,
            text_status=trust_verdict.text_status,
            rating_status=trust_verdict.rating_status,
            trust_score=trust_verdict.trust_score,
            ambiguity="none" if not analysis.features else analysis.features[0].ambiguity,
            ambiguity_mult=1.0 if not analysis.features else analysis.features[0].ambiguity_mult,
            embedding=analysis.embedding,
            stage_versions={"normalise": "1.0", "trust": "1.0", "extract": "1.0", "batch": "1.0"},
        )
        session.add(review_record)
        await session.flush()

        # Save Trust Gate Logs
        for g in trust_verdict.gates:
            gate_log = TrustGateLog(
                tenant_id=tenant_id,
                review_id=review_record.id,
                gate=g.gate,
                verdict=g.verdict,
                reason_code=g.reason_code,
                score_delta=g.score_delta,
                detail=g.detail,
            )
            session.add(gate_log)

        # Save Review Features
        for f in analysis.features:
            rf = ReviewFeature(
                tenant_id=tenant_id,
                review_id=review_record.id,
                feature=f.feature,
                polarity=f.polarity,
                score=f.score,
                ambiguity=f.ambiguity,
                sentence_idx=f.sentence_idx,
                anchor_sim=f.anchor_sim,
            )
            session.add(rf)

        # Save Serious Complaint if triggered
        if analysis.serious:
            sc = SeriousComplaint(
                tenant_id=tenant_id,
                review_id=review_record.id,
                category=analysis.serious.category,
                severity=analysis.serious.severity,
                urgency=analysis.serious.urgency,
                status="open",
                alerted_at=datetime.now(timezone.utc),
            )
            session.add(sc)
            await emit("serious.new", "done", run_id, tenant_id=tenant_id, review_id=review_record.id, session=session,
                       detail={"category": sc.category, "severity": sc.severity})

        await session.commit()
        return review_record.id
