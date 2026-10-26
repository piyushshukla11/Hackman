import sys
sys.path.insert(0, ".")

from ml.eval import ModelEvaluator

evaluator = ModelEvaluator()

sentiment_benchmark = [
    # Severe vernacular negative
    {"text": "Ekdum ghatiya bakwas quality hai bilkul mat khareedo", "rating": 1.0, "true_polarity": "neg"},
    {"text": "Waste of hard earned money, stopped working on day 2", "rating": 1.0, "true_polarity": "neg"},
    {"text": "Kharaab battery life, 1 ghante me discharge ho jata hai", "rating": 1.0, "true_polarity": "neg"},
    {"text": "Worst purchase ever, terrible customer support", "rating": 1.0, "true_polarity": "neg"},
    {"text": "Hinges snapped while opening the box, poor plastic", "rating": 1.0, "true_polarity": "neg"},
    # Positive vernacular / English
    {"text": "Zabardast sound quality, paisa wasool product!", "rating": 5.0, "true_polarity": "pos"},
    {"text": "Mast battery backup aur premium design", "rating": 5.0, "true_polarity": "pos"},
    {"text": "Exceptional noise cancellation and deep bass, loving it", "rating": 5.0, "true_polarity": "pos"},
    {"text": "Super fast charging and crystal clear display", "rating": 5.0, "true_polarity": "pos"},
    {"text": "Bahut accha laga, delivery bhi fast thi", "rating": 5.0, "true_polarity": "pos"},
    # Neutral
    {"text": "Average performance, nothing extraordinary", "rating": 3.0, "true_polarity": "neutral"},
    {"text": "The color is slightly darker than picture, works ok", "rating": 3.0, "true_polarity": "neutral"},
]

metrics = evaluator.evaluate_sentiment(sentiment_benchmark)
print("=== Sentiment Benchmark Metrics ===")
print(f"Accuracy:        {metrics['accuracy'] * 100:.1f}%")
print(f"Macro Precision: {metrics['macro_precision'] * 100:.1f}%")
print(f"Macro Recall:    {metrics['macro_recall'] * 100:.1f}%")
print(f"Macro F1:        {metrics['macro_f1'] * 100:.1f}%")
print(f"ECE (Error):     {metrics['ece']:.4f}")

hinglish_benchmark = [
    {"text": "Yeh phone garam hota hai aur battery khatam ho gayi", "is_hinglish": True},
    {"text": "Ekdum bakwas product hai bhai mat lo", "is_hinglish": True},
    {"text": "Bohot accha camera aur battery chal rahi hai", "is_hinglish": True},
    {"text": "Kharab sound quality hai aur volume bohot kam hai", "is_hinglish": True},
    {"text": "The sound quality is crisp and microphone works well", "is_hinglish": False},
    {"text": "Battery life lasts over two days on single charge", "is_hinglish": False},
    {"text": "Fast delivery and well packaged, no complaints", "is_hinglish": False},
    {"text": "Durable build and excellent ergonomic comfort", "is_hinglish": False},
]

h_metrics = evaluator.evaluate_hinglish(hinglish_benchmark)
print("\n=== Hinglish Detection Metrics ===")
print(f"Accuracy:        {h_metrics['accuracy'] * 100:.1f}%")
print(f"Macro F1:        {h_metrics['macro_f1'] * 100:.1f}%")
