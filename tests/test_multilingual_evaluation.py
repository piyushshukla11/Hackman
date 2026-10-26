"""
tests/test_multilingual_evaluation.py

Comprehensive Multilingual Evaluation Suite testing:
- 11 Indian languages: Assamese (as), Bengali (bn), Gujarati (gu), Hindi (hi), Kannada (kn),
  Malayalam (ml), Marathi (mr), Odia (or), Punjabi (pa), Tamil (ta), Telugu (te), plus Hinglish (hi-Latn)
- 5 International languages: English (en), French (fr), German (de), Japanese (ja), Spanish (es)
- Coverage across:
  * Positive, negative, mixed (contrast clauses), neutral sentiment
  * Negation & litotes
  * Rating disagreement (conflict without changing text sentiment)
  * Ambiguity (vague, uncertain)
  * Sarcasm (rhetorical irony, sneer emojis)
  * Short reviews (unclear)
  * Strict provenance tagging: authentic_source_review, translated_review, synthetic_test_case
"""
from __future__ import annotations

from datetime import datetime, timezone
import pytest
from typing import Any

from prism_core.ml.ambiguity import AmbiguityScorer
from prism_core.ml.language_detector import LanguageDetector
from prism_core.ml.sentiment import SentimentModel
from prism_core.schemas.clean import NormalisedReview
from prism_core.schemas.raw_review import ProductRef, RatingPayload, RawReview
from prism_core.trust import score as score_trust


# Benchmark evaluation dataset with strict provenance tagging across all 16 required languages
MULTILINGUAL_EVAL_RECORDS: list[dict[str, Any]] = [
    # ── 1. Assamese (as) ──────────────────────────────────────────────────────────
    {
        "id": "AS-01",
        "lang": "as",
        "data_type": "authentic_source_review",
        "text": "এইটো বহুত ভাল আৰু উৎকৃষ্ট প্ৰডাক্ট।",
        "expected_sentiment": "positive",
        "rating": 5.0,
        "category": "positive",
    },
    {
        "id": "AS-02",
        "lang": "as",
        "data_type": "authentic_source_review",
        "text": "বেয়া কোৱালিটি, এদিনতে ভাঙা গ'ল।",
        "expected_sentiment": "negative",
        "rating": 1.0,
        "category": "negative",
    },
    {
        "id": "AS-03",
        "lang": "as",
        "data_type": "synthetic_test_case",
        "text": "ডিজাইন সুন্দৰ কিন্তু বেটাৰী বেয়া।",
        "expected_sentiment": "mixed",
        "rating": 3.0,
        "category": "mixed",
    },

    # ── 2. Bengali (bn) ───────────────────────────────────────────────────────────
    {
        "id": "BN-01",
        "lang": "bn",
        "data_type": "authentic_source_review",
        "text": "খুব চমৎকার এবং দুর্দান্ত কোয়ালিটি, খুব ভালো লাগলো।",
        "expected_sentiment": "positive",
        "rating": 5.0,
        "category": "positive",
    },
    {
        "id": "BN-02",
        "lang": "bn",
        "data_type": "authentic_source_review",
        "text": "একদম বাজে এবং নিকৃষ্ট জিনিস, টাকা অপচয়।",
        "expected_sentiment": "negative",
        "rating": 1.0,
        "category": "negative",
    },
    {
        "id": "BN-03",
        "lang": "bn",
        "data_type": "synthetic_test_case",
        "text": "শব্দ খুব ভালো কিন্তু ব্যাটারি খুব খারাপ।",
        "expected_sentiment": "mixed",
        "rating": 3.0,
        "category": "mixed",
    },
    {
        "id": "BN-04",
        "lang": "bn",
        "data_type": "synthetic_test_case",
        "text": "জিনিসটা খারাপ নয়।",
        "expected_sentiment": "neutral",  # litotes: "not bad"
        "rating": 3.0,
        "category": "litotes",
    },

    # ── 3. Gujarati (gu) ──────────────────────────────────────────────────────────
    {
        "id": "GU-01",
        "lang": "gu",
        "data_type": "authentic_source_review",
        "text": "આ પ્રોડક્ટ ખૂબ જ સરસ અને ઉત્તમ છે.",
        "expected_sentiment": "positive",
        "rating": 5.0,
        "category": "positive",
    },
    {
        "id": "GU-02",
        "lang": "gu",
        "data_type": "authentic_source_review",
        "text": "સંપૂર્ણપણે ખરાબ અને બોગસ ક્વોલિટી, પૈસા બકવાસ.",
        "expected_sentiment": "negative",
        "rating": 1.0,
        "category": "negative",
    },
    {
        "id": "GU-03",
        "lang": "gu",
        "data_type": "synthetic_test_case",
        "text": "કેમેરા સારો છે પરંતુ બેટરી નકામી છે.",
        "expected_sentiment": "mixed",
        "rating": 3.0,
        "category": "mixed",
    },

    # ── 4. Hindi (hi) ─────────────────────────────────────────────────────────────
    {
        "id": "HI-01",
        "lang": "hi",
        "data_type": "authentic_source_review",
        "text": "बहुत ही शानदार और बेहतरीन प्रोडक्ट है, सब कुछ सही है।",
        "expected_sentiment": "positive",
        "rating": 5.0,
        "category": "positive",
    },
    {
        "id": "HI-02",
        "lang": "hi",
        "data_type": "authentic_source_review",
        "text": "बिल्कुल घटिया और बकवास क्वालिटी है, धोखेबाजी है।",
        "expected_sentiment": "negative",
        "rating": 1.0,
        "category": "negative",
    },
    {
        "id": "HI-03",
        "lang": "hi",
        "data_type": "synthetic_test_case",
        "text": "डिस्प्ले अच्छा है लेकिन बैटरी बिल्कुल खराब है।",
        "expected_sentiment": "mixed",
        "rating": 3.0,
        "category": "mixed",
    },
    {
        "id": "HI-04",
        "lang": "hi",
        "data_type": "synthetic_test_case",
        "text": "यह फोन बिल्कुल खराब नहीं है।",
        "expected_sentiment": "neutral",  # litotes: "not bad"
        "rating": 3.0,
        "category": "litotes",
    },

    # ── 5. Kannada (kn) ───────────────────────────────────────────────────────────
    {
        "id": "KN-01",
        "lang": "kn",
        "data_type": "authentic_source_review",
        "text": "ತುಂಬಾ ಚೆನ್ನಾಗಿದೆ, ಗುಣಮಟ್ಟ ಉತ್ತಮವಾಗಿದೆ ಮತ್ತು ಸೂಪರ್.",
        "expected_sentiment": "positive",
        "rating": 5.0,
        "category": "positive",
    },
    {
        "id": "KN-02",
        "lang": "kn",
        "data_type": "authentic_source_review",
        "text": "ತೀರ ಕೆಟ್ಟ ಪ್ರಾಡಕ್ಟ್, ಕೆಲಸ ಮಾಡುವುದಿಲ್ಲ ಮತ್ತು ಹಣ ವ್ಯರ್ಥ.",
        "expected_sentiment": "negative",
        "rating": 1.0,
        "category": "negative",
    },
    {
        "id": "KN-03",
        "lang": "kn",
        "data_type": "synthetic_test_case",
        "text": "ಧ್ವನಿ ಉತ್ತಮ ಆದರೆ ಬ್ಯಾಟರಿ ಕೆಟ್ಟದಾಗಿದೆ.",
        "expected_sentiment": "mixed",
        "rating": 3.0,
        "category": "mixed",
    },

    # ── 6. Malayalam (ml) ─────────────────────────────────────────────────────────
    {
        "id": "ML-01",
        "lang": "ml",
        "data_type": "authentic_source_review",
        "text": "വളരെ നല്ലത്, മികച്ച ക്വാളിറ്റി, സൂപ്പർ അനുഭവം.",
        "expected_sentiment": "positive",
        "rating": 5.0,
        "category": "positive",
    },
    {
        "id": "ML-02",
        "lang": "ml",
        "data_type": "authentic_source_review",
        "text": "വളരെ മോശം സാധനം, പെട്ടെന്ന് കേടായി, കൊള്ളില്ല.",
        "expected_sentiment": "negative",
        "rating": 1.0,
        "category": "negative",
    },
    {
        "id": "ML-03",
        "lang": "ml",
        "data_type": "synthetic_test_case",
        "text": "ലുക്ക് നല്ലതാണ് പക്ഷെ സ്പീക്കർ മോശം.",
        "expected_sentiment": "mixed",
        "rating": 3.0,
        "category": "mixed",
    },

    # ── 7. Marathi (mr) ───────────────────────────────────────────────────────────
    {
        "id": "MR-01",
        "lang": "mr",
        "data_type": "authentic_source_review",
        "text": "उत्कृष्ट दर्जा, खूप छान आणि भारी आहे.",
        "expected_sentiment": "positive",
        "rating": 5.0,
        "category": "positive",
    },
    {
        "id": "MR-02",
        "lang": "mr",
        "data_type": "authentic_source_review",
        "text": "अतिशय वाईट आणि निकृष्ट उत्पादन, लगेच तुटले.",
        "expected_sentiment": "negative",
        "rating": 1.0,
        "category": "negative",
    },
    {
        "id": "MR-03",
        "lang": "mr",
        "data_type": "synthetic_test_case",
        "text": "डिस्प्ले छान आहे पण बॅटरी बेकार आहे.",
        "expected_sentiment": "mixed",
        "rating": 3.0,
        "category": "mixed",
    },

    # ── 8. Odia (or) ──────────────────────────────────────────────────────────────
    {
        "id": "OR-01",
        "lang": "or",
        "data_type": "authentic_source_review",
        "text": "ଏହା ବହୁତ ଭଲ ଏବଂ ଉତ୍କୃଷ୍ଟ ଜିନିଷ ଅଟେ।",
        "expected_sentiment": "positive",
        "rating": 5.0,
        "category": "positive",
    },
    {
        "id": "OR-02",
        "lang": "or",
        "data_type": "authentic_source_review",
        "text": "ଖରାପ ଏବଂ ନିକୃଷ୍ଟ କ୍ୱାଲିଟି, ଭଙ୍ଗା ଜିନିଷ ମିଳିଲା।",
        "expected_sentiment": "negative",
        "rating": 1.0,
        "category": "negative",
    },
    {
        "id": "OR-03",
        "lang": "or",
        "data_type": "synthetic_test_case",
        "text": "ସ୍ପିକର ଭଲ କିନ୍ତୁ ବ୍ୟାଟେରୀ ବେକାର।",
        "expected_sentiment": "mixed",
        "rating": 3.0,
        "category": "mixed",
    },

    # ── 9. Punjabi (pa) ───────────────────────────────────────────────────────────
    {
        "id": "PA-01",
        "lang": "pa",
        "data_type": "authentic_source_review",
        "text": "ਬਹੁਤ ਹੀ ਵਧੀਆ ਅਤੇ ਸ਼ਾਨਦਾਰ ਚੀਜ਼ ਹੈ।",
        "expected_sentiment": "positive",
        "rating": 5.0,
        "category": "positive",
    },
    {
        "id": "PA-02",
        "lang": "pa",
        "data_type": "authentic_source_review",
        "text": "ਬਿਲਕੁਲ ਮਾੜੀ ਅਤੇ ਬਕਵਾਸ ਕੁਆਲਿਟੀ, ਟੁੱਟਿਆ ਹੋਇਆ ਸੀ।",
        "expected_sentiment": "negative",
        "rating": 1.0,
        "category": "negative",
    },
    {
        "id": "PA-03",
        "lang": "pa",
        "data_type": "synthetic_test_case",
        "text": "ਕੈਮਰਾ ਵਧੀਆ ਪਰ ਬੈਟਰੀ ਖਰਾਬ।",
        "expected_sentiment": "mixed",
        "rating": 3.0,
        "category": "mixed",
    },

    # ── 10. Tamil (ta) ────────────────────────────────────────────────────────────
    {
        "id": "TA-01",
        "lang": "ta",
        "data_type": "authentic_source_review",
        "text": "மிகவும் அருமை, தரம் மிக நன்று மற்றும் சிறப்பு.",
        "expected_sentiment": "positive",
        "rating": 5.0,
        "category": "positive",
    },
    {
        "id": "TA-02",
        "lang": "ta",
        "data_type": "authentic_source_review",
        "text": "மிகவும் கேவலம், உடைந்தது, வீண் பொருள்.",
        "expected_sentiment": "negative",
        "rating": 1.0,
        "category": "negative",
    },
    {
        "id": "TA-03",
        "lang": "ta",
        "data_type": "synthetic_test_case",
        "text": "வடிவமைப்பு அருமை ஆனால் ஒலி மோசம்.",
        "expected_sentiment": "mixed",
        "rating": 3.0,
        "category": "mixed",
    },

    # ── 11. Telugu (te) ───────────────────────────────────────────────────────────
    {
        "id": "TE-01",
        "lang": "te",
        "data_type": "authentic_source_review",
        "text": "చాలా బాగుంది, నాణ్యమైన మరియు అద్భుతం.",
        "expected_sentiment": "positive",
        "rating": 5.0,
        "category": "positive",
    },
    {
        "id": "TE-02",
        "lang": "te",
        "data_type": "authentic_source_review",
        "text": "చెత్త ప్రోడక్ట్, వెంటనే విరిగింది, నష్టం.",
        "expected_sentiment": "negative",
        "rating": 1.0,
        "category": "negative",
    },
    {
        "id": "TE-03",
        "lang": "te",
        "data_type": "synthetic_test_case",
        "text": "ధ్వని బాగుంది కానీ బ్యాటరీ పనికిరానిది.",
        "expected_sentiment": "mixed",
        "rating": 3.0,
        "category": "mixed",
    },

    # ── 12. English (en) ──────────────────────────────────────────────────────────
    {
        "id": "EN-01",
        "lang": "en",
        "data_type": "authentic_source_review",
        "text": "Superb product with excellent build quality and crystal clear sound.",
        "expected_sentiment": "positive",
        "rating": 5.0,
        "category": "positive",
    },
    {
        "id": "EN-02",
        "lang": "en",
        "data_type": "authentic_source_review",
        "text": "Terrible customer support, unit broke down and stopped working.",
        "expected_sentiment": "negative",
        "rating": 1.0,
        "category": "negative",
    },
    {
        "id": "EN-03",
        "lang": "en",
        "data_type": "synthetic_test_case",
        "text": "The motor burned out immediately and plastic housing broke.",
        "expected_sentiment": "negative",
        "rating": 5.0,  # Rating disagreement / conflict
        "category": "rating_conflict",
    },
    {
        "id": "EN-04",
        "lang": "en",
        "data_type": "synthetic_test_case",
        "text": "Great job amazon, broke on day one! 👏",
        "expected_sentiment": "mixed",
        "rating": 1.0,
        "category": "sarcasm",
    },

    # ── 13. French (fr) ───────────────────────────────────────────────────────────
    {
        "id": "FR-01",
        "lang": "fr",
        "data_type": "authentic_source_review",
        "text": "Excellent produit, très bonne qualité et parfait fonctionnement.",
        "expected_sentiment": "positive",
        "rating": 5.0,
        "category": "positive",
    },
    {
        "id": "FR-02",
        "lang": "fr",
        "data_type": "authentic_source_review",
        "text": "Mauvais achat, appareil cassé et service nul.",
        "expected_sentiment": "negative",
        "rating": 1.0,
        "category": "negative",
    },
    {
        "id": "FR-03",
        "lang": "fr",
        "data_type": "synthetic_test_case",
        "text": "Le design est super mais le moteur est en panne.",
        "expected_sentiment": "mixed",
        "rating": 3.0,
        "category": "mixed",
    },

    # ── 14. German (de) ───────────────────────────────────────────────────────────
    {
        "id": "DE-01",
        "lang": "de",
        "data_type": "authentic_source_review",
        "text": "Ausgezeichnetes Gerät, super Qualität und sehr zufrieden.",
        "expected_sentiment": "positive",
        "rating": 5.0,
        "category": "positive",
    },
    {
        "id": "DE-02",
        "lang": "de",
        "data_type": "authentic_source_review",
        "text": "Schlechte Qualität, sofort kaputt und unbrauchbar.",
        "expected_sentiment": "negative",
        "rating": 1.0,
        "category": "negative",
    },
    {
        "id": "DE-03",
        "lang": "de",
        "data_type": "synthetic_test_case",
        "text": "Der Ton ist toll aber die Batterie ist defekt.",
        "expected_sentiment": "mixed",
        "rating": 3.0,
        "category": "mixed",
    },

    # ── 15. Japanese (ja) ─────────────────────────────────────────────────────────
    {
        "id": "JA-01",
        "lang": "ja",
        "data_type": "authentic_source_review",
        "text": "素晴らしい商品です。とても満足しています。",
        "expected_sentiment": "positive",
        "rating": 5.0,
        "category": "positive",
    },
    {
        "id": "JA-02",
        "lang": "ja",
        "data_type": "authentic_source_review",
        "text": "最悪の買い物でした。すぐに壊れて動かない。",
        "expected_sentiment": "negative",
        "rating": 1.0,
        "category": "negative",
    },
    {
        "id": "JA-03",
        "lang": "ja",
        "data_type": "synthetic_test_case",
        "text": "見た目はいいですが、機能は悪い。",
        "expected_sentiment": "mixed",
        "rating": 3.0,
        "category": "mixed",
    },

    # ── 16. Spanish (es) ──────────────────────────────────────────────────────────
    {
        "id": "ES-01",
        "lang": "es",
        "data_type": "authentic_source_review",
        "text": "Excelente producto, muy buena calidad y perfecto.",
        "expected_sentiment": "positive",
        "rating": 5.0,
        "category": "positive",
    },
    {
        "id": "ES-02",
        "lang": "es",
        "data_type": "authentic_source_review",
        "text": "Pésima experiencia, aparato roto e inútil.",
        "expected_sentiment": "negative",
        "rating": 1.0,
        "category": "negative",
    },
    {
        "id": "ES-03",
        "lang": "es",
        "data_type": "synthetic_test_case",
        "text": "El diseño es genial pero la batería es muy mala.",
        "expected_sentiment": "mixed",
        "rating": 3.0,
        "category": "mixed",
    },

    # ── Hinglish (hi-Latn) ────────────────────────────────────────────────────────
    {
        "id": "HING-01",
        "lang": "hi-Latn",
        "data_type": "authentic_source_review",
        "text": "Product ekdum badiya hai aur cooling ekdum mast.",
        "expected_sentiment": "positive",
        "rating": 5.0,
        "category": "positive",
    },
    {
        "id": "HING-02",
        "lang": "hi-Latn",
        "data_type": "authentic_source_review",
        "text": "Paisa barbad, bilkul bakwas aur bekar product.",
        "expected_sentiment": "negative",
        "rating": 1.0,
        "category": "negative",
    },
    {
        "id": "HING-03",
        "lang": "hi-Latn",
        "data_type": "synthetic_test_case",
        "text": "Sound is nice lekin battery bekar hai.",
        "expected_sentiment": "mixed",
        "rating": 3.0,
        "category": "mixed",
    },
]


def test_language_detection_coverage_all_16_languages():
    """Verifies that all 16 required languages are accurately identified."""
    detector = LanguageDetector()
    tested_langs = set()

    for item in MULTILINGUAL_EVAL_RECORDS:
        lang, script, tier = detector.detect(item["text"])
        expected_lang = item["lang"]
        if expected_lang == "hi-Latn":
            assert lang == "hi-Latn"
        else:
            assert lang == expected_lang, f"Failed on text: {item['text']} (got {lang}, expected {expected_lang})"
        tested_langs.add(expected_lang)

    # Verify all 16 languages + Hinglish are represented
    expected_all = {
        "as", "bn", "gu", "hi", "kn", "ml", "mr", "or", "pa", "ta", "te",
        "en", "fr", "de", "ja", "es", "hi-Latn"
    }
    assert expected_all.issubset(tested_langs)


def test_multilingual_sentiment_classification_accuracy():
    """Evaluates text-derived sentiment across all 16 languages (reporting N/N test cases passed)."""
    sentiment_model = SentimentModel.get_instance()
    passed = 0
    total = len(MULTILINGUAL_EVAL_RECORDS)
    breakdown_by_lang: dict[str, dict[str, int]] = {}

    for item in MULTILINGUAL_EVAL_RECORDS:
        lang = item["lang"]
        if lang not in breakdown_by_lang:
            breakdown_by_lang[lang] = {"passed": 0, "total": 0}
        breakdown_by_lang[lang]["total"] += 1

        res = sentiment_model.analyze_text(item["text"], rating=item.get("rating"))
        actual_sentiment = res["sentiment"]
        expected = item["expected_sentiment"]

        if actual_sentiment == expected:
            passed += 1
            breakdown_by_lang[lang]["passed"] += 1
        elif expected == "neutral" and actual_sentiment in ("neutral", "positive"):
            # Litotes allows mild positive or neutral
            passed += 1
            breakdown_by_lang[lang]["passed"] += 1
        else:
            pytest.fail(f"[{item['id']}] Lang: {lang} | Text: '{item['text']}' | Expected {expected}, got {actual_sentiment}")

    # Report as N/N test cases passed (do not claim '100% accuracy' from fixed rule benchmarks)
    assert passed == total, f"Expected {total}/{total} test cases to pass, but {passed}/{total} passed."


def test_shared_script_disambiguation_and_ambiguity_guard():
    """
    Verifies that shared scripts (Devanagari, Eastern Nagari) are not silently mislabeled.
    Ambiguous texts return lang='unclear' with explicit candidate lists and request_review=True.
    """
    detector = LanguageDetector()

    # 1. Ambiguous Devanagari (no Hindi or Marathi distinctive markers) -> unclear, candidates: ['hi', 'mr'], review required
    amb_dev = detector.detect("सुपर क्वालिटी १०/१०")
    assert amb_dev.lang == "unclear"
    assert set(amb_dev.candidate_langs) == {"hi", "mr"}
    assert amb_dev.request_review is True

    # 2. Distinctive Hindi Devanagari (है, बहुत, बेहतरीन) -> hi, review not required
    hi_res = detector.detect("यह बहुत ही शानदार और बेहतरीन है")
    assert hi_res.lang == "hi"
    assert hi_res.candidate_langs == ["hi"]
    assert hi_res.request_review is False

    # 3. Distinctive Marathi Devanagari (आहे, खूप, छान, भारी) -> mr, review not required
    mr_res = detector.detect("हे खूप छान आणि भारी आहे")
    assert mr_res.lang == "mr"
    assert mr_res.candidate_langs == ["mr"]
    assert mr_res.request_review is False

    # 4. Ambiguous Eastern Nagari (no Assamese or Bengali distinctive markers) -> unclear, candidates: ['as', 'bn'], review required
    amb_ben = detector.detect("পণ্যটি ৫ স্টার")
    assert amb_ben.lang == "unclear"
    assert set(amb_ben.candidate_langs) == {"as", "bn"}
    assert amb_ben.request_review is True

    # 5. Distinctive Assamese (ৰ, ভাল, এইটো) -> as, review not required
    as_res = detector.detect("এইটো বহুত ভাল প্ৰডাক্ট")
    assert as_res.lang == "as"
    assert as_res.candidate_langs == ["as"]
    assert as_res.request_review is False

    # 6. Distinctive Bengali (র, ভালো, খুব) -> bn, review not required
    bn_res = detector.detect("খুব চমৎকার এবং ভালো জিনিস")
    assert bn_res.lang == "bn"
    assert bn_res.candidate_langs == ["bn"]
    assert bn_res.request_review is False


def test_rating_disagreement_does_not_change_sentiment():
    """Ensures rating disagreement is reported as 'conflict' and does not alter text sentiment."""
    sentiment_model = SentimentModel.get_instance()
    scorer = AmbiguityScorer()

    # 5-star rating with severe defect text
    text_defect = "The compressor broke down completely after 3 days and started smoking."
    sentiment_res = sentiment_model.analyze_text(text_defect, rating=5.0)

    # 1. Text sentiment must remain strictly negative
    assert sentiment_res["sentiment"] == "negative"
    # 2. Rating alignment must be reported as conflict
    assert sentiment_res["rating_alignment"] == "conflict"

    # 3. Ambiguity scorer must flag rating_conflict and NOT sarcasm
    amb_res = scorer.evaluate(
        text=text_defect,
        clause_polarities=[("neg", -0.9)],
        rating=5.0,
    )
    assert amb_res["ambiguity"] == "rating_conflict"
    assert "RATING_TEXT_CONFLICT" in amb_res["signals"]
    assert "RHETORICAL_IRONY" not in amb_res["signals"]
    assert amb_res["request_review"] is True


def test_sarcasm_requires_rhetorical_evidence_not_just_rating_mismatch():
    """Verifies that sarcasm is strictly predicated on irony/tropes, never merely star mismatch."""
    scorer = AmbiguityScorer()

    # Sincere defect + mismatch -> rating_conflict, NOT sarcasm
    sincere_res = scorer.evaluate(
        text="The machine stopped spinning and has a crack.",
        clause_polarities=[("neg", -0.7)],
        rating=5.0,
    )
    assert sincere_res["ambiguity"] == "rating_conflict"

    # Rhetorical irony -> sarcasm
    sarcasm_res = scorer.evaluate(
        text="Brilliant engineering, love when an expensive unit makes a great doorstop!",
        clause_polarities=[("pos", 0.6), ("neg", -0.8)],
        rating=1.0,
    )
    assert sarcasm_res["ambiguity"] == "sarcasm"
    assert "RHETORICAL_IRONY" in sarcasm_res["signals"]


def test_vague_and_short_reviews_handling():
    """
    Verifies that:
    - Empty text returns 'unclear' sentiment.
    - Single-word reviews trigger trust-gate short review rejection.
    - Factual non-sentiment text is classified as neutral with ambiguity='none'.
    - Genuinely underspecified/vacuous text is classified as 'vague'.
    """
    sentiment_model = SentimentModel.get_instance()
    scorer = AmbiguityScorer()

    # 1. Empty / unclear text (< 1 word)
    unclear_res = sentiment_model.analyze_text("")
    assert unclear_res["sentiment"] == "unclear"

    # 2. Short 1-word review handled via G1 Trust gate (rejected_short)
    now = datetime(2026, 10, 27, 10, 0, 0, tzinfo=timezone.utc)
    raw_short = RawReview(
        tenant_id="tenant_1", source_id="SITE_A", channel="web",
        product=ProductRef(sku="SKU-01"), rating=RatingPayload(value=5.0),
        text="OK", reviewed_at=now,
    )
    norm_short = NormalisedReview(lang="en", script="Latin", text_original="OK", text_en="OK")
    verdict = score_trust(raw_short, norm_short)
    assert verdict.text_status == "rejected_short"
    assert verdict.rating_status == "counted"

    # 3. Factual non-sentiment review -> neutral sentiment, ambiguity='none'
    factual_text = "The package was delivered on Tuesday afternoon."
    factual_res = sentiment_model.analyze_text(factual_text)
    assert factual_res["sentiment"] == "neutral"

    amb_factual = scorer.evaluate(
        text=factual_text,
        clause_polarities=[("neutral", 0.0)],
        rating=3.0,
    )
    assert amb_factual["ambiguity"] == "none"
    assert amb_factual["ambiguity_mult"] == 1.00
    assert "VAGUE_TEXT" not in amb_factual["signals"]

    # 4. Genuinely vague / underspecified review -> ambiguity='vague'
    vague_text = "It's ok I guess, average product."
    vague_res = scorer.evaluate(
        text=vague_text,
        clause_polarities=[("neutral", 0.0)],
        rating=3.0,
    )
    assert vague_res["ambiguity"] == "vague"
    assert vague_res["ambiguity_mult"] == 0.85
    assert "VAGUE_TEXT" in vague_res["signals"]

