"""
seeds/generate_seeds.py

Deterministic Seed Data Generator:
Generates ~1,500 realistic customer reviews across:
- 4 Products (Headphones, Smartwatch, Smart Flask, Earbuds)
- 6 Simulated E-Commerce Sites (SITE_A to SITE_F)
- 16 Weeks timeline
- Multiple Indic languages & Hinglish
- Ground-truth defect spikes in specific batches (e.g. BATCH-2024-W12 hinge failure)
- Includes ground-truth labels for evaluation harness
"""
from __future__ import annotations

import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

random.seed(42)

PRODUCTS = [
    {"id": "prod_headphone", "sku": "PRD-ANC-001", "name": "AuraWave Wireless ANC Headphones", "category": "Audio"},
    {"id": "prod_smartwatch", "sku": "PRD-SMW-002", "name": "PulseTrack Pro Smartwatch", "category": "Wearables"},
    {"id": "prod_flask", "sku": "PRD-FLS-003", "name": "HydroSmart Temperature Flask", "category": "Smart Home"},
    {"id": "prod_earbuds", "sku": "PRD-TWS-004", "name": "AirFlow True Wireless Earbuds", "category": "Audio"},
]

CHANNELS = ["SITE_A_web", "SITE_B_app", "SITE_C_webhook", "SITE_D_marketplace", "SITE_E_quick_vote", "SITE_F_csv_export"]
BATCHES = ["BATCH-2024-W10", "BATCH-2024-W11", "BATCH-2024-W12", "BATCH-2024-W13", "BATCH-2024-W14"]

SAMPLE_REVIEWS = [
    # Clean English
    {"text": "Sound quality is remarkably clear and ear cushions are very comfortable.", "rating": 5.0, "lang": "en", "feature": "sound_quality", "is_spam": False},
    {"text": "Battery life lasts around 22 hours, impressive for this price point.", "rating": 4.5, "lang": "en", "feature": "battery", "is_spam": False},
    {"text": "The bluetooth connectivity keeps dropping when walking outside.", "rating": 2.0, "lang": "en", "feature": "connectivity", "is_spam": False},
    # Defect concentration on hinge in BATCH-2024-W12
    {"text": "The left hinge snapped completely after 3 days of normal folding. Very fragile plastic.", "rating": 1.0, "lang": "en", "feature": "durability", "is_spam": False, "batch": "BATCH-2024-W12"},
    {"text": "Hinge crack on day one! Seems like brittle plastic used in this batch.", "rating": 1.0, "lang": "en", "feature": "durability", "is_spam": False, "batch": "BATCH-2024-W12"},
    {"text": "Plastic hinge broke near the adjustment headband. Unusable.", "rating": 1.5, "lang": "en", "feature": "durability", "is_spam": False, "batch": "BATCH-2024-W12"},
    # Hinglish
    {"text": "ye product bilkul bekar hai, mera paisa barbaad ho gaya mat khareedo", "rating": 1.0, "lang": "hi-Latn", "feature": "durability", "is_spam": False},
    {"text": "zabardast sound quality hai, battery bhi ek number chalti hai", "rating": 5.0, "lang": "hi-Latn", "feature": "sound_quality", "is_spam": False},
    {"text": "sound badiya hai lekin ear cushion comfort bilkul bekar hai", "rating": 3.0, "lang": "hi-Latn", "feature": "comfort", "is_spam": False},
    # Indic Devanagari
    {"text": "बैटरी बैकअप बहुत शानदार है और आवाज़ एकदम साफ है।", "rating": 5.0, "lang": "hi", "feature": "battery", "is_spam": False},
    {"text": "प्लास्टिक की गुणवत्ता बहुत खराब है, एक हफ्ते में टूट गया।", "rating": 1.0, "lang": "hi", "feature": "durability", "is_spam": False, "batch": "BATCH-2024-W12"},
    # Sarcasm
    {"text": "Great job team! The headphone literally stopped charging after exactly 2 hours.", "rating": 5.0, "lang": "en", "feature": "battery", "is_sarcasm": True, "is_spam": False},
    # Spam / Promo
    {"text": "Visit http://freegiftcards.biz and use code DISCOUNT99 for free cash", "rating": 5.0, "lang": "en", "feature": "spam", "is_spam": True},
    # Safety risk
    {"text": "The charger got burning hot and smoke started coming out of the battery port!", "rating": 1.0, "lang": "en", "feature": "battery", "is_safety": True, "is_spam": False},
]


def generate_seed_dataset(output_path: Path | None = None) -> list[dict]:
    dataset = []
    base_date = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    for i in range(1500):
        prod = random.choice(PRODUCTS)
        channel = random.choice(CHANNELS)
        template = random.choice(SAMPLE_REVIEWS)
        days_offset = random.randint(0, 112)  # 16 weeks
        rev_date = base_date + timedelta(days=days_offset, hours=random.randint(0, 23))

        batch = template.get("batch") or random.choice(BATCHES)

        record = {
            "id": f"rev_seed_{i:04d}",
            "tenant_id": "default",
            "source_id": channel.split("_")[0],
            "channel": channel,
            "product_sku": prod["sku"],
            "product_name": prod["name"],
            "text": template["text"],
            "rating": template["rating"],
            "reviewed_at": rev_date.isoformat(),
            "batch_code": batch,
            "verified_buyer": random.random() > 0.25,
            # Ground truth labels for eval harness
            "ground_truth": {
                "lang": template["lang"],
                "target_feature": template["feature"],
                "is_spam": template.get("is_spam", False),
                "is_sarcasm": template.get("is_sarcasm", False),
                "is_safety": template.get("is_safety", False),
                "batch": batch,
            },
        }
        dataset.append(record)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)

    return dataset


if __name__ == "__main__":
    out_file = Path(__file__).parent / "dataset.json"
    generate_seed_dataset(out_file)
    print(f"Generated 1,500 seed reviews into {out_file}")
