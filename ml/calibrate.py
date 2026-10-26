"""
ml/calibrate.py

Confidence Calibration and Temperature Scaling:
Optimizes temperature parameter tau for confidence waterfall:
C_calibrated = 1 / (1 + exp(- (z / tau)))
where z = logit(C_raw).
Provides Platt scaling and isotonic regression wrappers.
"""
from __future__ import annotations

import math
from typing import Sequence
import numpy as np


def logit(p: float, eps: float = 1e-6) -> float:
    """Clamped logit function."""
    p_clamped = max(eps, min(1.0 - eps, p))
    return float(np.log(p_clamped / (1.0 - p_clamped)))


def sigmoid(z: float) -> float:
    """Sigmoid function."""
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    else:
        ez = math.exp(z)
        return ez / (1.0 + ez)


class TemperatureScaler:
    """
    Fits a single temperature scalar T > 0 on validation logits
    to minimize Negative Log Likelihood (NLL).
    """

    def __init__(self, initial_temperature: float = 1.0):
        self.temperature = max(0.01, initial_temperature)

    def fit(self, confidences: Sequence[float], labels: Sequence[bool], lr: float = 0.05, max_iter: int = 100) -> float:
        """
        Gradient descent on temperature T over validation binary labels.
        """
        if len(confidences) != len(labels) or len(confidences) == 0:
            return self.temperature

        logits = np.array([logit(c) for c in confidences], dtype=np.float64)
        y = np.array([1.0 if l else 0.0 for l in labels], dtype=np.float64)

        t = self.temperature
        for _ in range(max_iter):
            scaled_logits = logits / t
            probs = 1.0 / (1.0 + np.exp(-np.clip(scaled_logits, -30.0, 30.0)))

            # Gradient of NLL w.r.t temperature T
            # d(NLL)/dT = sum((probs - y) * (-logits / T^2))
            grad = np.sum((probs - y) * (-logits / (t ** 2))) / len(logits)

            # Update step
            t -= lr * grad
            t = max(0.1, min(10.0, t))

        self.temperature = round(float(t), 4)
        return self.temperature

    def calibrate(self, raw_confidence: float) -> float:
        """Apply calibrated temperature scaling to a raw confidence score [0, 1]."""
        z = logit(raw_confidence)
        calibrated = sigmoid(z / self.temperature)
        return round(calibrated, 4)
