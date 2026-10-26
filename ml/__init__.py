"""
ml package

Clean exports of PRISM Machine Learning and Vernacular NLP modules:
- EmbeddingProvider (multilingual-e5-small, intfloat, 384-d, ONNX)
- SentimentModel (augmented VADER + Indian e-commerce lexicon + rating prior)
- LanguageDetector (Unicode script-block analysis)
- HinglishDetector (Indic function words)
- Translator (in-memory PII masking, Sarvam API, Gemini fallback)
- AmbiguityScorer (6 heuristic ambiguity/sarcasm signals)
- LLMClient (Gemini structured outputs & RAG question generator)
- ModelEvaluator & TemperatureScaler
"""
from ml.embeddings import EmbeddingProvider
from ml.sentiment import SentimentModel
from ml.language_detector import LanguageDetector
from ml.hinglish_detector import HinglishDetector
from ml.translator import Translator, mask_pii, restore_pii
from ml.ambiguity import AmbiguityScorer
from ml.llm_client import LLMClient
from ml.eval import ModelEvaluator, compute_classification_metrics, compute_expected_calibration_error
from ml.calibrate import TemperatureScaler

__all__ = [
    "EmbeddingProvider",
    "SentimentModel",
    "LanguageDetector",
    "HinglishDetector",
    "Translator",
    "mask_pii",
    "restore_pii",
    "AmbiguityScorer",
    "LLMClient",
    "ModelEvaluator",
    "compute_classification_metrics",
    "compute_expected_calibration_error",
    "TemperatureScaler",
]
