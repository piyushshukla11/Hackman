"""
prism_core/ml/ambiguity.py

L3 Understand — Disentangled Ambiguity & Sarcasm Engine.
Maintains strict separation between:
1. Vague text (genuinely underspecified, vacuous, or uninterpretable — distinct from factual neutral)
2. Factual neutral text (clear factual assertions with neutral sentiment -> ambiguity='none')
3. Mixed sentiment (conflicting positive and negative clauses)
4. Rating/text conflict (rating mismatch without irony — NEVER classified as sarcasm)
5. Sarcasm (genuine rhetorical irony, sneer emojis, sarcastic tropes)
6. Language / translation uncertainty (unclear shared scripts or low translation confidence)

Provides:
- ambiguity: 'none' | 'vague' | 'mixed' | 'rating_conflict' | 'sarcasm' | 'uncertain'
- ambiguity_mult: heuristic rule-based confidence penalty (0.55 to 1.00; pending human calibration)
- request_review: boolean flag when human verification is recommended
- signals: granular boolean indicator list
"""
from __future__ import annotations

import re
from typing import Optional, Sequence, Tuple
import yaml

from prism_core.config.settings import get_settings

SARCASTIC_EMOJIS = {"🙃", "🙄", "👏", "😒", "🤡", "🤦", "🤦‍♂️", "🤦‍♀️"}

IRONIC_PATTERNS = [
    re.compile(r"\b(great\s+job|bravo|congratulations)\b.*?\b(broke|failed|garbage|worst|useless|ruined)\b", re.IGNORECASE),
    re.compile(r"\b(makes\s+a\s+great|expensive)\s+(paperweight|doorstop|brick|frizzbee)\b", re.IGNORECASE),
    re.compile(r"\b(love\s+(?:how|when|it\s+when))\b.*?\b(died|stopped\s+working|broke|melted)\b", re.IGNORECASE),
    re.compile(r"\b(best\s+part\s+is\s+it\s+doesn't\s+work|10/10\s+if\s+you\s+like\s+wasting)\b", re.IGNORECASE),
    re.compile(r"\b(brilliant\s+(?:engineering|design))\b.*?\b(terrible|disaster|hazard)\b", re.IGNORECASE),
    re.compile(r"\b(kya\s+baat\s+hai|shabash|wah\s+re\s+wah)\b", re.IGNORECASE),
    re.compile(r"(?:^|\s)/s(?:\s|$|[.!?])", re.IGNORECASE),
]

RHETORICAL_PATTERNS = [
    re.compile(r"\b(who\s+(?:designed|engineered|approved)\s+this)\b", re.IGNORECASE),
    re.compile(r"\b(is\s+this\s+a\s+joke)\b", re.IGNORECASE),
]

VAGUE_EXPRESSIONS = {
    "ok", "okay", "fine", "average", "normal", "so so", "so-so", "meh", "whatever",
    "hmm", "just ok", "seems ok", "it's ok", "its ok", "it is ok", "thik hai", "theek hai",
    "thik thak", "theek thak", "kuch khas nahi", "kam chalau", "samanya"
}

VAGUE_PATTERNS = [
    re.compile(r"^(ok|okay|fine|average|normal|so[\s-]so|meh|whatever|hmm|just\s+ok|seems\s+ok|it'?s\s+ok)[.!]?$", re.IGNORECASE),
    re.compile(r"\b(it'?s\s+ok\s+i\s+guess|nothing\s+special|not\s+sure|don'?t\s+know|neither\s+good\s+nor\s+bad|can'?t\s+say|hard\s+to\s+say|average\s+product|it'?s\s+alright|as\s+expected|it\s+is\s+what\s+it\s+is)\b", re.IGNORECASE),
    re.compile(r"\b(काम\s+चलाऊ|ठीक\s+ठाक|कुछ\s+खास\s+नहीं|पता\s+नहीं|सामान्य)\b", re.IGNORECASE),
]


class AmbiguityScorer:
    """Disentangles sarcasm, rating conflicts, mixed sentiment, language uncertainty, and vague text."""

    def __init__(self, thresholds_path: Optional[str] = None):
        settings = get_settings()
        cfg_path = thresholds_path or (settings.config_dir / "thresholds.yaml")
        # Rule-based heuristic multipliers (will be empirically calibrated once human annotations are completed)
        self.mults = {
            "none": 1.00,
            "vague": 0.85,
            "rating_conflict": 0.75,
            "mixed": 0.70,
            "uncertain": 0.65,
            "sarcasm": 0.55,
        }
        if cfg_path.exists():
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                loaded = data.get("weights", {}).get("ambiguity_multipliers", {})
                if isinstance(loaded, dict):
                    self.mults.update(loaded)
            except Exception:
                pass

    def evaluate(
        self,
        text: str,
        clause_polarities: Sequence[Tuple[str, float]],
        rating: Optional[float] = None,
        emojis: Optional[Sequence[str]] = None,
        translation_uncertainty: bool = False,
        language_uncertainty: bool = False,
    ) -> dict:
        """
        Evaluate text, clause polarities, rating, and translation state for ambiguity.
        - Factual neutral text is classified with ambiguity='none' (not vague).
        - Genuinely underspecified/vacuous text is classified as 'vague'.
        - A rating mismatch alone NEVER produces sarcasm.
        - Language and translation uncertainty are tracked separately.
        """
        signals: list[str] = []
        text_clean = (text or "").strip()
        words = text_clean.split()

        # 1. Sarcastic Emojis
        has_sarcastic_emoji = any(e in SARCASTIC_EMOJIS for e in (emojis or []))
        if has_sarcastic_emoji:
            signals.append("SARCASTIC_EMOJI")

        # 2. Rhetorical Irony
        has_irony = any(bool(p.search(text_clean)) for p in IRONIC_PATTERNS)
        if has_irony:
            signals.append("RHETORICAL_IRONY")

        # 3. Rhetorical Questions
        has_rhetorical = any(bool(p.search(text_clean)) for p in RHETORICAL_PATTERNS)
        if has_rhetorical:
            signals.append("RHETORICAL_QUESTION")

        # 4. Mixed Polarity (contrasting positive and negative clauses in same review)
        pos_count = sum(1 for pol, _ in clause_polarities if pol == "pos")
        neg_count = sum(1 for pol, _ in clause_polarities if pol == "neg")
        has_mixed = pos_count > 0 and neg_count > 0
        if has_mixed:
            signals.append("MIXED_POLARITY")

        # 5. Rating vs Text Conflict (Separate from Sarcasm)
        has_rating_conflict = False
        if rating is not None:
            if rating >= 4.0 and neg_count > pos_count and neg_count >= 1:
                has_rating_conflict = True
                signals.append("RATING_TEXT_CONFLICT")
            elif rating <= 2.0 and pos_count > neg_count and pos_count >= 1:
                has_rating_conflict = True
                signals.append("RATING_TEXT_CONFLICT")

        # 6. Language & Translation Uncertainty
        if translation_uncertainty:
            signals.append("TRANSLATION_UNCERTAINTY")
        if language_uncertainty:
            signals.append("LANGUAGE_UNCERTAINTY")

        # 7. Vague Text vs Factual Neutral Check
        # Factual neutral statements (e.g. delivery day, technical specs, dimensions)
        # are informative neutral, NOT vague.
        # Use 'vague' ONLY when text is genuinely underspecified, vacuous, or uninterpretable.
        clean_lower = text_clean.lower().strip(" .!?,;")
        matches_vague_expression = clean_lower in VAGUE_EXPRESSIONS or any(bool(p.search(text_clean)) for p in VAGUE_PATTERNS)
        is_short_vacuous = (len(words) < 3 and not any(char.isdigit() for char in text_clean) and not has_irony and not has_rating_conflict)

        is_vague = matches_vague_expression or (is_short_vacuous and (not clause_polarities or all(pol == "neutral" for pol, _ in clause_polarities)))

        if is_vague and not has_irony and not has_sarcastic_emoji and not has_rating_conflict:
            signals.append("VAGUE_TEXT")

        # Classification Logic (Strict Disentanglement)
        # Sarcasm requires genuine rhetorical irony or sneer cues
        if has_irony or (has_sarcastic_emoji and (has_mixed or has_rating_conflict or neg_count > 0)):
            ambiguity_label = "sarcasm"
        elif has_rating_conflict:
            # Rating conflict alone is NEVER sarcasm
            ambiguity_label = "rating_conflict"
        elif has_mixed:
            ambiguity_label = "mixed"
        elif translation_uncertainty or language_uncertainty:
            ambiguity_label = "uncertain"
        elif is_vague:
            ambiguity_label = "vague"
        else:
            ambiguity_label = "none"

        mult = float(self.mults.get(ambiguity_label, 1.00))

        # Request review flag when evidence is weak, contradictory, or ambiguous
        request_review = (
            ambiguity_label in ("rating_conflict", "sarcasm", "uncertain") or
            translation_uncertainty or
            language_uncertainty or
            (is_vague and len(words) < 2)
        )

        return {
            "ambiguity": ambiguity_label,
            "ambiguity_mult": mult,
            "signals": signals,
            "request_review": request_review,
        }

    def score(
        self,
        text: str,
        user_rating: Optional[float] = 3.0,
        sentiment_polarity: float = 0.0,
        emojis: Optional[Sequence[str]] = None,
    ) -> Tuple[str, float]:
        """
        Backward compatibility entrypoint for MVP tests expecting (label, mult).
        """
        if user_rating is not None:
            if user_rating >= 4.0 and sentiment_polarity <= -0.5:
                return ("sarcasm", float(self.mults.get("sarcasm", 0.55)))
            if user_rating <= 2.0 and sentiment_polarity >= 0.5:
                return ("sarcasm", float(self.mults.get("sarcasm", 0.55)))

        text_lower = (text or "").lower()
        hedge_words = {"maybe", "sort of", "kind of", "perhaps", "possibly", "not sure"}
        if any(h in text_lower for h in hedge_words) or any(bool(p.search(text)) for p in VAGUE_PATTERNS):
            return ("vague", float(self.mults.get("vague", 0.85)))

        if "/s" in text or any(bool(p.search(text)) for p in IRONIC_PATTERNS) or any(e in SARCASTIC_EMOJIS for e in (emojis or [])):
            return ("sarcasm", float(self.mults.get("sarcasm", 0.55)))

        return ("none", float(self.mults.get("none", 1.00)))


