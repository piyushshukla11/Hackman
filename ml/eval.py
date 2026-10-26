"""
ml/eval.py

Evaluation suite for PRISM ML components:
- Sentiment classification metrics (Accuracy, Precision, Recall, Macro-F1)
- Hinglish detection accuracy
- Language classification accuracy
- Ambiguity scoring calibration
- Computes calibration error (Expected Calibration Error - ECE)
"""
from __future__ import annotations

import math
from typing import Sequence, Tuple
import numpy as np

from ml.sentiment import SentimentModel
from ml.hinglish_detector import HinglishDetector
from ml.language_detector import LanguageDetector


def compute_classification_metrics(y_true: Sequence[str], y_pred: Sequence[str]) -> dict[str, float]:
    """Compute Accuracy, Macro Precision, Macro Recall, and Macro F1."""
    if not y_true or len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must be non-empty and of equal length.")

    classes = sorted(list(set(y_true) | set(y_pred)))
    n = len(y_true)
    correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp)
    accuracy = correct / n

    precisions = []
    recalls = []
    f1s = []

    for c in classes:
        tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == c and yp == c)
        fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt != c and yp == c)
        fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == c and yp != c)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        precisions.append(prec)
        recalls.append(rec)
        f1s.append(f1)

    macro_precision = float(np.mean(precisions))
    macro_recall = float(np.mean(recalls))
    macro_f1 = float(np.mean(f1s))

    return {
        "accuracy": round(accuracy, 4),
        "macro_precision": round(macro_precision, 4),
        "macro_recall": round(macro_recall, 4),
        "macro_f1": round(macro_f1, 4),
        "n_samples": n,
        "classes": classes,
    }


def compute_expected_calibration_error(
    confidences: Sequence[float],
    accuracies: Sequence[bool],
    n_bins: int = 10,
) -> float:
    """
    Computes Expected Calibration Error (ECE):
    ECE = sum_b (|acc(B_b) - conf(B_b)| * |B_b| / N)
    """
    if len(confidences) != len(accuracies) or len(confidences) == 0:
        return 0.0

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    n = len(confidences)
    ece = 0.0

    for i in range(n_bins):
        low, high = bins[i], bins[i + 1]
        bin_indices = [
            idx for idx, c in enumerate(confidences)
            if (low <= c < high) or (i == n_bins - 1 and low <= c <= high)
        ]
        if not bin_indices:
            continue

        bin_conf = np.mean([confidences[idx] for idx in bin_indices])
        bin_acc = np.mean([1.0 if accuracies[idx] else 0.0 for idx in bin_indices])
        bin_weight = len(bin_indices) / n

        ece += abs(bin_acc - bin_conf) * bin_weight

    return round(float(ece), 4)


class ModelEvaluator:
    """Evaluates all core ML components against benchmark datasets."""

    def __init__(self):
        self.sentiment_model = SentimentModel.get_instance()
        self.hinglish_detector = HinglishDetector()
        self.language_detector = LanguageDetector()

    def evaluate_sentiment(self, samples: Sequence[dict]) -> dict[str, float]:
        """
        Expects samples with 'text', 'rating', and 'true_polarity' ('pos' | 'neg' | 'neutral').
        """
        y_true = [s["true_polarity"] for s in samples]
        y_pred = []
        confidences = []
        accuracies = []

        for s in samples:
            pol, score = self.sentiment_model.score_sentence(s["text"], s.get("rating", 3.0))
            y_pred.append(pol)
            conf = min(1.0, abs(score) + 0.2)
            confidences.append(conf)
            accuracies.append(pol == s["true_polarity"])

        metrics = compute_classification_metrics(y_true, y_pred)
        ece = compute_expected_calibration_error(confidences, accuracies)
        metrics["ece"] = ece
        return metrics

    def evaluate_hinglish(self, samples: Sequence[dict]) -> dict[str, float]:
        """
        Expects samples with 'text' and 'is_hinglish' (bool).
        """
        y_true = ["hinglish" if s["is_hinglish"] else "other" for s in samples]
        y_pred = ["hinglish" if self.hinglish_detector.is_hinglish(s["text"]) else "other" for s in samples]
        return compute_classification_metrics(y_true, y_pred)
