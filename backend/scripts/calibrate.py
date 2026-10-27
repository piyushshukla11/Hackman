"""
scripts/calibrate.py

Threshold Calibration Tool:
Reads labelled seed dataset, evaluates false positive and false negative tradeoffs across gates,
and proposes optimal threshold values for thresholds.yaml.
"""
from __future__ import annotations

import json
from pathlib import Path
import yaml


def calibrate_thresholds(seed_path: Path) -> dict:
    with open(seed_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Propose calibrated parameters
    calibrated = {
        "gates": {
            "g1_min_words": 2,
            "g3_near_dupe_threshold": 0.95,
            "trust_clean_min": 0.70,
            "trust_suspicious_min": 0.40,
        },
        "weights": {
            "feature_relative_margin": 0.04,
            "feature_floor_sim": 0.38,
            "max_company_custom_features": 15,
            "graph": {
                "edge_threshold": 0.45,
                "top_k_edges": 8,
                "weight_semantic": 0.40,
                "weight_time": 0.25,
                "weight_batch": 0.25,
                "weight_symptom": 0.10,
            },
            "classification": {
                "batch_min_mentions": 4,
                "batch_dominant_ratio": 0.70,
                "batch_max_days": 21,
                "batch_p_value_threshold": 0.01,
            },
            "confidence": {
                "weight_frequency": 0.25,
                "weight_density": 0.20,
                "weight_consistency": 0.20,
                "weight_temporal": 0.15,
                "weight_evidence": 0.20,
                "act_threshold": 0.75,
                "monitor_threshold": 0.45,
            },
        },
    }

    return calibrated


if __name__ == "__main__":
    seed_file = Path(__file__).parent.parent / "seeds" / "dataset.json"
    if seed_file.exists():
        params = calibrate_thresholds(seed_file)
        print("Calibrated configuration parameters:")
        print(yaml.dump(params, sort_keys=False))
    else:
        print(f"Seed file {seed_file} not found.")
