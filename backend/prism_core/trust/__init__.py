"""
prism_core/trust/__init__.py

L2 Clean — Trust Cascade G1 through G6.
Calculates trust score, assigns verdict, and determines text_status and rating_status.

Gates:
G1: Length (min words)
G2: Exact duplicate
G3: Near-duplicate (vector similarity >= 0.95)
G4: Content heuristics (promo, URLs, phone numbers, emoji spam)
G5: Burst & coordination patterns
G6: Provenance & verified purchase
"""
from __future__ import annotations

import re
from typing import Any
from prism_core.config.settings import get_settings
from prism_core.schemas.clean import GateResult, NormalisedReview, TrustVerdict
from prism_core.schemas.raw_review import RawReview

URL_REGEX = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
PHONE_REGEX = re.compile(r"(\+?91[\-\s]?)?[6-9]\d{9}\b|\b\d{3}[-.\s]??\d{3}[-.\s]??\d{4}\b")
PROMO_KEYWORDS = {"use code", "coupon code", "discount code", "flat off", "telegram link", "whatsapp group"}


def count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def score(
    review: NormalisedReview,
    raw: RawReview | None = None,
    is_exact_dupe: bool = False,
    near_dupe_max_sim: float = 0.0,
    burst_detected: bool = False,
) -> TrustVerdict:
    """
    Public entrypoint for L2 Trust Cascade.
    Evaluates gates G1 to G6 and returns TrustVerdict.
    """
    gates: list[GateResult] = []
    current_score = 1.0
    text = (review.text_original or "").strip()
    words = count_words(text)

    # ── G1: Length Gate ──────────────────────────────────────────────────────────
    if words == 0:
        gates.append(GateResult(
            gate="G1",
            verdict="pass",
            reason_code="RATING_ONLY",
            score_delta=0.0,
            detail={"word_count": 0},
        ))
        return TrustVerdict(
            trust_score=1.0,
            verdict="clean",
            text_status="none",
            rating_status="counted",
            gates=gates,
        )
    elif words < 2:
        gates.append(GateResult(
            gate="G1",
            verdict="warn",
            reason_code="SHORT_TEXT",
            score_delta=-0.10,
            detail={"word_count": words},
        ))
        current_score -= 0.10
    else:
        gates.append(GateResult(
            gate="G1",
            verdict="pass",
            reason_code="ADEQUATE_LENGTH",
            score_delta=0.0,
            detail={"word_count": words},
        ))

    # ── G2: Exact Duplicate Gate ─────────────────────────────────────────────────
    if is_exact_dupe:
        delta = -0.90
        current_score += delta
        gates.append(GateResult(
            gate="G2",
            verdict="fail",
            reason_code="EXACT_DUP",
            score_delta=delta,
            detail={"is_exact_dupe": True},
        ))
    else:
        gates.append(GateResult(gate="G2", verdict="pass", reason_code="UNIQUE_TEXT", score_delta=0.0))

    # ── G3: Near-Duplicate Gate (HNSW Cosine >= 0.95) ─────────────────────────────
    if near_dupe_max_sim >= 0.95:
        delta = -0.65
        current_score += delta
        gates.append(GateResult(
            gate="G3",
            verdict="fail",
            reason_code="NEAR_DUP",
            score_delta=delta,
            detail={"max_similarity": near_dupe_max_sim},
        ))
    else:
        gates.append(GateResult(
            gate="G3",
            verdict="pass",
            reason_code="DISTINCT_VECTOR",
            score_delta=0.0,
            detail={"max_similarity": near_dupe_max_sim},
        ))

    # ── G4: Content Heuristics Gate ──────────────────────────────────────────────
    has_url = bool(URL_REGEX.search(text))
    has_phone = bool(PHONE_REGEX.search(text))
    has_promo = any(kw in text.lower() for kw in PROMO_KEYWORDS)
    repeated_emojis = len(review.emojis) >= 5

    if has_url or has_promo or has_phone:
        delta = -0.80
        current_score += delta
        gates.append(GateResult(
            gate="G4",
            verdict="fail",
            reason_code="PROMO_LINK_SPAM",
            score_delta=delta,
            detail={"has_url": has_url, "has_promo": has_promo, "has_phone": has_phone},
        ))
    elif repeated_emojis:
        delta = -0.20
        current_score += delta
        gates.append(GateResult(
            gate="G4",
            verdict="warn",
            reason_code="REPEATED_EMOJIS",
            score_delta=delta,
            detail={"emoji_count": len(review.emojis)},
        ))
    else:
        gates.append(GateResult(gate="G4", verdict="pass", reason_code="CLEAN_CONTENT", score_delta=0.0))

    # ── G5: Burst & Coordination Gate ────────────────────────────────────────────
    if burst_detected:
        delta = -0.40
        current_score += delta
        gates.append(GateResult(
            gate="G5",
            verdict="warn",
            reason_code="BURST_COORDINATION",
            score_delta=delta,
            detail={"burst_detected": True},
        ))
    else:
        gates.append(GateResult(gate="G5", verdict="pass", reason_code="NORMAL_CADENCE", score_delta=0.0))

    # ── G6: Provenance & Verification Gate ───────────────────────────────────────
    is_verified = False
    if raw and (raw.author.verified_buyer or (raw.order and raw.order.order_id)):
        is_verified = True

    if is_verified:
        bonus = 0.15
        current_score += bonus
        gates.append(GateResult(
            gate="G6",
            verdict="pass",
            reason_code="VERIFIED_PURCHASE",
            score_delta=bonus,
            detail={"verified": True},
        ))
    else:
        gates.append(GateResult(
            gate="G6",
            verdict="warn",
            reason_code="UNVERIFIED_PURCHASE",
            score_delta=0.0,
            detail={"verified": False},
        ))

    # Clamp final trust score between 0.0 and 1.0
    final_score = max(0.0, min(1.0, round(current_score, 2)))

    # Determine verdicts and statuses
    if is_exact_dupe or near_dupe_max_sim >= 0.95:
        verdict = "rejected"
        text_status = "rejected_dup"
        rating_status = "excluded"
    elif has_url or has_promo or has_phone:
        verdict = "rejected"
        text_status = "rejected_spam"
        rating_status = "excluded"
    elif words < 2:
        verdict = "clean"
        text_status = "rejected_short"
        rating_status = "counted"
    elif final_score >= 0.70:
        verdict = "clean"
        text_status = "accepted"
        rating_status = "counted"
    elif final_score >= 0.40:
        verdict = "suspicious"
        text_status = "accepted"
        rating_status = "downweighted"
    else:
        verdict = "rejected"
        text_status = "rejected_spam"
        rating_status = "excluded"

    return TrustVerdict(
        trust_score=final_score,
        verdict=verdict,
        text_status=text_status,
        rating_status=rating_status,
        gates=gates,
    )
