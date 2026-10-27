"""
scripts/direct_seed_llm.py

Fast, zero-API-cost direct database seeder for PRISM.
Populates PostgreSQL / SQLite directly with structured reviews produced by external LLMs
(e.g., ChatGPT, Claude, Gemini) without consuming Sarvam API credits or pipeline wait time.

Usage:
    python backend/scripts/direct_seed_llm.py --file path/to/llm_output.json
    python backend/scripts/direct_seed_llm.py --file path/to/llm_output.jsonl --tenant-id default
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prism_core.db.base import get_sessionmaker
from prism_core.db.models import (
    Batch,
    Product,
    ProductVersion,
    RawReview,
    Review,
    ReviewFeature,
    SeriousComplaint,
    TrustGateLog,
)
from prism_core.ml.embeddings import EmbeddingProvider


def make_id(prefix: str, val: str) -> str:
    h = hashlib.sha256(val.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{h}"


async def seed_from_file(file_path: Path, tenant_id: str = "default") -> dict[str, int]:
    if not file_path.exists():
        raise FileNotFoundError(f"Data file not found at: {file_path}")

    # Load records (supports JSON array or JSONL)
    raw_content = file_path.read_text(encoding="utf-8").strip()
    records: list[dict[str, Any]] = []

    if raw_content.startswith("["):
        records = json.loads(raw_content)
    else:
        for line in raw_content.splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))

    print(f"Loaded {len(records)} records from {file_path.name}")

    sessionmaker = get_sessionmaker()
    embedder = EmbeddingProvider.get_instance()

    stats = {
        "products": 0,
        "batches": 0,
        "reviews": 0,
        "features": 0,
        "serious": 0,
    }

    async with sessionmaker() as session:
        # Cache existing products and batches to avoid duplicate key violations
        existing_prods_res = await session.execute(select(Product).where(Product.tenant_id == tenant_id))
        products_cache: dict[str, Product] = {p.id: p for p in existing_prods_res.scalars().all()}
        for p in list(products_cache.values()):
            products_cache[p.name.lower()] = p

        existing_batches_res = await session.execute(select(Batch).where(Batch.tenant_id == tenant_id))
        batches_cache: dict[str, Batch] = {b.code: b for b in existing_batches_res.scalars().all()}

        for idx, rec in enumerate(records, 1):
            prod_name = rec.get("product_name") or rec.get("brand") or "Generic Product"
            category = rec.get("category") or "General"
            prod_sku = rec.get("product_sku") or make_id("SKU", prod_name)
            prod_key = prod_name.lower()

            # 1. Resolve or create Product
            if prod_key not in products_cache:
                prod_id = make_id("prod", prod_name)
                product = Product(
                    id=prod_id,
                    tenant_id=tenant_id,
                    name=prod_name,
                    category=category,
                    custom_features=[{"name": f} for f in rec.get("expected_features", [])],
                    specs={"category": category, "brand": rec.get("brand")},
                )
                session.add(product)
                await session.flush()

                # Add default version
                ver = ProductVersion(
                    id=make_id("ver", f"{prod_id}_v1.0"),
                    tenant_id=tenant_id,
                    product_id=prod_id,
                    label="v1.0",
                    effective_from=date(2024, 1, 1),
                    notes="Initial release",
                )
                session.add(ver)
                await session.flush()

                products_cache[prod_key] = product
                products_cache[prod_id] = product
                stats["products"] += 1
            else:
                product = products_cache[prod_key]

            # 2. Resolve or create Batch
            batch_code = rec.get("batch_code") or "BATCH-2024-W12"
            if batch_code not in batches_cache:
                batch = Batch(
                    id=make_id("batch", f"{product.id}_{batch_code}"),
                    tenant_id=tenant_id,
                    product_id=product.id,
                    code=batch_code,
                    mfg_start=date(2024, 3, 1),
                    mfg_end=date(2024, 3, 31),
                )
                session.add(batch)
                await session.flush()
                batches_cache[batch_code] = batch
                stats["batches"] += 1
            else:
                batch = batches_cache[batch_code]

            # 3. Create RawReview
            rev_id_str = rec.get("id") or rec.get("sample_id") or str(uuid.uuid4())
            idempotency_key = make_id("idem", f"{tenant_id}_{rev_id_str}")

            # Check if review already inserted
            existing_rev = await session.execute(
                select(Review.id).where(Review.tenant_id == tenant_id, Review.id == rev_id_str)
            )
            if existing_rev.scalar_one_or_none():
                continue

            raw_review = RawReview(
                id=make_id("raw", rev_id_str),
                tenant_id=tenant_id,
                source_id=rec.get("source_id") or "direct_llm_seed",
                idempotency_key=idempotency_key,
                kind="review",
                payload=rec,
                received_at=datetime.now(timezone.utc),
            )
            session.add(raw_review)
            await session.flush()

            # 4. Canonical Review
            rating_val = float(rec.get("rating") or 3.0)
            text_original = rec.get("text_original") or rec.get("text") or ""
            text_en = rec.get("text_en") or rec.get("source_text_en") or text_original
            lang = rec.get("lang") or rec.get("language_code") or "en"
            script = rec.get("script") or "Latin"

            # Compute local embedding vector (384-d)
            try:
                emb_vec = embedder.embed_passage(text_en or text_original)
            except Exception:
                emb_vec = embedder._deterministic_mock_vector(text_en or text_original)

            # Dates
            reviewed_at_str = rec.get("reviewed_at")
            if reviewed_at_str:
                try:
                    rev_dt = datetime.fromisoformat(reviewed_at_str.replace("Z", "+00:00"))
                except Exception:
                    rev_dt = datetime.now(timezone.utc)
            else:
                rev_dt = datetime.now(timezone.utc)

            canonical_review = Review(
                id=rev_id_str,
                raw_id=raw_review.id,
                tenant_id=tenant_id,
                product_id=product.id,
                source_id=raw_review.source_id,
                channel=rec.get("channel") or "marketplace",
                rating=rating_val,
                rating_raw=str(rating_val),
                rating_scale="5_star",
                text_original=text_original,
                text_en=text_en,
                lang=lang,
                script=script,
                reviewed_at=rev_dt,
                verified_purchase=rec.get("verified_purchase", True),
                author_hash=rec.get("author_hash") or make_id("usr", rev_id_str),
                batch_id=batch.id,
                batch_method=rec.get("batch_method") or "B1",
                batch_conf=rec.get("batch_conf", 0.95),
                text_status=rec.get("text_status") or "accepted",
                rating_status=rec.get("rating_status") or "counted",
                trust_score=float(rec.get("trust_score", 1.0)),
                ambiguity=rec.get("ambiguity") or "none",
                ambiguity_mult=float(rec.get("ambiguity_mult", 1.0)),
                embedding=emb_vec,
                stage_versions={"llm_seed": "1.0"},
            )
            session.add(canonical_review)
            await session.flush()
            stats["reviews"] += 1

            # 5. Trust Gate Log (all pass)
            t_gate = TrustGateLog(
                tenant_id=tenant_id,
                review_id=canonical_review.id,
                gate="G1",
                verdict="pass",
                reason_code="VERIFIED_REVIEW",
                score_delta=0.0,
                detail={"source": "llm_direct_seed"},
            )
            session.add(t_gate)

            # 6. Features & Aspects
            features_list = rec.get("features") or []
            if not features_list and rec.get("feature"):
                features_list = [{
                    "feature": rec["feature"],
                    "polarity": "pos" if rating_val >= 3.5 else "neg",
                    "score": 0.8 if rating_val >= 3.5 else -0.8,
                }]

            for f_idx, feat in enumerate(features_list):
                rf = ReviewFeature(
                    tenant_id=tenant_id,
                    review_id=canonical_review.id,
                    feature=feat.get("feature", "general_quality"),
                    polarity=feat.get("polarity", "pos" if rating_val >= 3.5 else "neg"),
                    score=float(feat.get("score", 0.8)),
                    ambiguity=feat.get("ambiguity", canonical_review.ambiguity),
                    sentence_idx=f_idx,
                    anchor_sim=0.9,
                )
                session.add(rf)
                stats["features"] += 1

            # 7. Serious Complaints (Safety / Injury)
            serious_data = rec.get("serious")
            if serious_data:
                sc = SeriousComplaint(
                    tenant_id=tenant_id,
                    review_id=canonical_review.id,
                    category=serious_data.get("category", "safety"),
                    severity=serious_data.get("severity", "high"),
                    urgency=serious_data.get("urgency", "high"),
                    status="open",
                    alerted_at=datetime.now(timezone.utc),
                )
                session.add(sc)
                stats["serious"] += 1

            if idx % 100 == 0:
                await session.flush()
                print(f"Processed {idx}/{len(records)} reviews...")

        await session.commit()

    print("\nDatabase Direct Seeding Complete!")
    print(f"- Products Created/Updated: {stats['products']}")
    print(f"- Batches Linked:           {stats['batches']}")
    print(f"- Reviews Inserted:         {stats['reviews']}")
    print(f"- Feature Aspects Stored:   {stats['features']}")
    print(f"- Serious Complaints:       {stats['serious']}")
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="PRISM Direct LLM Review Seeder")
    parser.add_argument("--file", "-f", type=Path, required=True, help="Path to JSON or JSONL file")
    parser.add_argument("--tenant-id", "-t", type=str, default="default", help="Tenant ID (default: 'default')")
    args = parser.parse_args()

    asyncio.run(seed_from_file(args.file, args.tenant_id))


if __name__ == "__main__":
    main()
