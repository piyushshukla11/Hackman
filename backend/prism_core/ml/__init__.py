"""
prism_core/ml

Re-exports core ML components from top-level `ml` package with fallback.
"""
from __future__ import annotations

try:
    from ml.embeddings import EmbeddingProvider
    from ml.sentiment import SentimentModel
    from ml.language_detector import LanguageDetector
    from ml.hinglish_detector import HinglishDetector
    from ml.translator import Translator, mask_pii, restore_pii
    from ml.ambiguity import AmbiguityScorer
    from ml.llm_client import LLMClient
except ImportError:
    from prism_core.ml.embeddings import EmbeddingProvider  # type: ignore
    from prism_core.ml.sentiment import SentimentModel  # type: ignore
    from prism_core.ml.language_detector import LanguageDetector  # type: ignore
    from prism_core.ml.hinglish_detector import HinglishDetector  # type: ignore
    from prism_core.ml.translator import Translator, mask_pii, restore_pii  # type: ignore
    from prism_core.ml.ambiguity import AmbiguityScorer  # type: ignore
    from prism_core.ml.llm_client import LLMClient  # type: ignore

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
]
